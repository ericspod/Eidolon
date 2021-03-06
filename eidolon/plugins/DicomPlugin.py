# Eidolon Biomedical Framework
# Copyright (C) 2016-8 Eric Kerfoot, King's College London, all rights reserved
#
# This file is part of Eidolon.
#
# Eidolon is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Eidolon is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program (LICENSE.txt).  If not, see <http://www.gnu.org/licenses/>


#PACS: https://github.com/patmun/pynetdicom http://www.dicomserver.co.uk/


import os
import sys
import threading
import mmap
import datetime
import time
import re
import zipfile
import unittest
import tempfile
import shutil
import glob
import itertools
from collections import OrderedDict, namedtuple
from random import randint
import numpy as np
from io import BytesIO

try:
    from StringIO import StringIO
except:
    from io import StringIO

from eidolon import (
    vec3, rotator, color, enum, concurrent, timing, queue, first, taskroutine, clamp, taskmethod, fillList, avgspan,
    ImageScenePlugin, ImageSceneObject, ImageSceneObjectRepr, BaseCamera2DWidget, SharedImage, Qt, QtWidgets, Future
)
import eidolon

eidolon.addLibraryFile('pydicom-1.3.0.dev0-py2.py3-none-any') # PyDicom: https://github.com/darcymason/pydicom

from pydicom.dicomio import read_file
from pydicom.datadict import DicomDictionary
from pydicom.tag import Tag
from pydicom.dataset import Dataset,FileDataset

from ..ui import Ui_SeriesProp, Ui_ChooseSeriesDialog, Ui_Dicom2DView


eidolon.AssetType.append('dcm','Dicom Sources','Dicom Datasets (Directory References)') # adds the DICOM directory asset type to the asset panel
digestFilename='dicomdataset.ini' # name of digest file
headerPrecision=4 # precision of float values in DICOM headers, values are only correct to this number plus one of significant figures
keywordToTag={v[4]:Tag(k) for k,v in DicomDictionary.items()} # maps tag keywords to 2 part tag numbers

positionTag='ImagePositionPatient'
orientationTag='ImageOrientationPatient'
slopeTag='RescaleSlope'
interTag='RescaleIntercept'
seriesTag='SeriesInstanceUID'
spacingTag='PixelSpacing'
rowsTag='Rows'
colsTag='Columns'
triggerTag='TriggerTime'
commentTag='ImageComments'
afterStart=Tag(0x0019,0x1016) # tag for [TimeAfterStart]

# non-standard Dicom tags that are used by different groups
NonstandardTags=enum(
    ('USpixdimx',  Tag(0x0018, 0x602c)),
    ('USpixdimy',  Tag(0x0018, 0x602e)),
    ('USpixdimz',  Tag(0x3001, 0x1003)),
    ('USnumframes',Tag(0x0028, 0x0008)),
    ('USheight',   Tag(0x0028, 0x0010)),
    ('USwidth',    Tag(0x0028, 0x0011)),
    ('USdepth',    Tag(0x3001, 0x1001)),
    ('USpixeldata',Tag(0x7fe0, 0x0010))
)


def roundHeaderVals(*vals):
    '''Yield each of `vals' rounded to `headerPrecision'.'''
    for v in vals:
        yield round(v,headerPrecision)


def readDicomMMap(fullpath,**kwargs):
    with open(fullpath,'r+b') as ff:
        mm=mmap.mmap(ff.fileno(),0)
        try:
            return read_file(mm,**kwargs)
        finally:
            mm.close()


def readDicomHeartRate(series_or_dcm):
    '''
    Attempt to retrieve the heart rate in BPM from the DicomSeries or Dicom object `series_or_dcm'. If the "HeartRate"
    tag is present then this is used, otherwise attempt to parse the RR or bpm value from the "ImageComments" tag if
    this is present. The comment should be something like "RR 1153 +/- 41; 138 heartbeats" or contain a BPM value like
    "56 bpm" for this to work. If no heart rate is found then return None.
    '''
    if isinstance(series_or_dcm,DicomSeries):
        dcm=series_or_dcm.loadDicomFile(0)
    else:
        dcm=series_or_dcm

    heartrate=dcm.get('HeartRate',None)

    # if the HeartRate tag isn't given attempt to parse the RR time from the comment field
    if not heartrate:
        comment=dcm.get(commentTag,'')
        m1=re.search('RR\s*(\d+)\s*',comment)

        if m1:
            heartrate=60000/int(m1.groups()[0])
        else:
            m2=re.search('(\d+)\s*[Bb][Pp][Mm]',comment)
            if m2:
                heartrate=int(m2.groups()[0])

    return heartrate


def readDicomTimeValue(series_or_dcm):
    '''
    Attempt to determine a timing value from the DicomSeries or Dicom object `series_or_dcm'. This will try to use the
    TriggerTime tag but will then attempt to read a phase value from the ImageComment tag, this should work for CT
    images which don't use TriggerTime. Returns the determined time or -1 if none was found.
    '''
    if isinstance(series_or_dcm,DicomSeries):
        dcm=series_or_dcm.loadDicomFile(0)
    else:
        dcm=series_or_dcm

    trigger=dcm.get(triggerTag,None)
    if trigger is not None:
        return float(trigger)
    
    fromstart=dcm.get(afterStart,None)
    if fromstart is not None:
        return float(fromstart.value)

    m=re.search('(\d+)\s*%',dcm.get(commentTag,''))
    if m:
        return float(m.groups()[0])
    
    return -1


def createDicomReadThread(rootpath,files,readPixels=True):
    '''
    Reads the Dicom files in `rootpath' listed by relative file names in the list  `files', and returns the reading
    thread object and the synchronized queue containing (relative-filenames,Dicom-object) pairs produced by the thread.
    '''
    dcmqueue=queue.Queue()

    def readDicoms():
        for f in files:
            try:
                fullpath=os.path.abspath(os.path.join(rootpath,f))
                dcm=read_file(fullpath,stop_before_pixels=(not readPixels))
                dcmqueue.put((f,dcm))
            except: # reject non-Dicom files or files with errors
                pass

    readthread=threading.Thread(target=readDicoms)
    readthread.start()

    return readthread,dcmqueue


@concurrent
def createDicomDatasets(process,rootdir,files):
    '''Reads the listed Dicom files from the given directory and returns DicomDataset objects containing collected info.'''
    dds=DicomDataset(rootdir)

    readthread,dcmqueue=createDicomReadThread(rootdir,files,False)

    counter=0
    while readthread.isAlive() or not dcmqueue.empty():
        try:
            f,ds=dcmqueue.get(True,0.01)

            series=dds.getSeries(ds.SeriesInstanceUID,True)
            series.addFile(os.path.relpath(f,rootdir))
            series.desc=series.desc or str(ds.get('SeriesDescription',series.desc)).strip()
            series.seriesNum=series.seriesNum or int(ds.get('SeriesNumber',series.seriesNum))

            counter+=1
            process.setProgress(counter)
        except:
            pass

    return dds


@concurrent
#@timing
def loadSharedImages(process,rootdir,files,crop=None):
    '''Reads the image data from the listed files and returns a list of SharedImage objects storing this image data.'''
    result=[]
#    eidolon.printFlush(process.index,'Start')

    for i in range(len(files)):
        process.setProgress(i+1)
        filename=os.path.join(rootdir,files[i])
#        eidolon.printFlush(process.index,i,files[i])
        dcm=DicomSharedImage(filename,i+process.startval,False)
#        eidolon.printFlush(process.index,i,files[i],'Done')

        # crop the image if a valid crop rectangle is given and the object has image data
        if dcm.img is not None and crop!=None and (crop[0]>0 or crop[1]>0 or crop[2]<dcm.dimensions[0]-1 or crop[3]<dcm.dimensions[1]-1):
            dcm=dcm.crop(*crop)

        # if the img member is None and this isn't a compressed image then it's non-image data so discard
        if dcm.img is not None or dcm.isCompressed:
            dcm.setShared(True)
            result.append(dcm)
            
#    eidolon.printFlush(process.index,'Done')
    return result


@timing
def loadDicomZipFile(filename, includeTags=False):
    dds=DicomDataset(filename)
    
    with zipfile.ZipFile(filename) as z:
        for n in z.namelist():
            s=BytesIO(z.read(n))
            try:
                ds=read_file(s)
            except:
                pass # ignore files which aren't Dicom files
            else:
                dsi=DicomSharedImage(n,dcm=ds,includeTags=includeTags)
                
                series=dds.getSeries(ds.SeriesInstanceUID,True)
                series.addFile(n)
                series.addSharedImages([dsi])
                series.desc=series.desc or str(ds.get('SeriesDescription',series.desc)).strip()
                series.seriesNum=series.seriesNum or int(ds.get('SeriesNumber',series.seriesNum))
            
    return dds


def convertToDict(dcm):
    def _datasetToDict(dcm):
        result=OrderedDict()
        for elem in dcm:
            name=elem.name
            value=_elemToValue(elem)
            if value:
                result[elem.tag]=(name,value)

        return result

    def _elemToValue(elem):
        value=None
        if elem.VR=='SQ':
            value=OrderedDict()
            for i,item in enumerate(elem):
                value['item_%i'%i]=_datasetToDict(item)
        elif elem.name!='Pixel Data':
            value=elem.value

        return value

    return _datasetToDict(dcm)


def addDicomTagsToMap(dcm,tagmap):

    def _datasetToDict(dcm):
        result=OrderedDict()
        for elem in dcm:
            name=elem.name
            value=_elemToValue(elem)
            tag=(elem.tag.group,elem.tag.elem)

            if value:
                result[tag]=(name,value)

        return result

    def _elemToValue(elem):
        value=None
        if elem.VR=='SQ':
            value=OrderedDict()
            for i,item in enumerate(elem):
                value['item_%i'%i]=_datasetToDict(item)
        elif elem.name!='Pixel Data':
            value=elem.value
            if not eidolon.isPicklable(value):
                value=str(value)

        return value

    for elem in dcm:
        name=elem.name
        value=_elemToValue(elem)
        #tag=(elem.tag.group,elem.tag.elem)

        if value:
            if name not in tagmap:
                tagmap[name]=[value]
            elif len(tagmap[name])>1 or (len(tagmap[name])==1 and tagmap[name][0]!=value):
                tagmap[name].append(value)


def getSeriesTagMap(series):
    tags={}

    for i in range(len(series.filenames)):
        addDicomTagsToMap(series.loadDicomFile(i),tags)

    for k,v in tags.items():
        try:
            if len(set(v))==1:
                tags[k]=[v[0]]
        except TypeError:
            pass

    return tags


def isPhaseImage(image):
    '''Returns True if the SharedImage or Dicom image object `image' has a tag field indicating the image is phase.'''
    imagetype=list(getattr(image,'imageType',None) or image.get('ImageType',[])) # imageType in SharedImage, ImageType in Dicom

    # these are the members of imagetype which should indicate phase image for the different manufacturers
    # (see https://uk.mathworks.com/matlabcentral/fileexchange/31978-readdicomdir-indir-debuglevel-reply-/content/ReadDicomDir.m)
    phasevalue1='PHASE MAP' # philips?
    phasevalue2='P' # Siemens?

    return phasevalue1 in imagetype or phasevalue2 in imagetype


def extractOverlay(image):
    '''
    Given a SharedImage with its Dicom tags present, extract the overlay data and assign it to the image matrix of the
    returned copy of `image'. If `image' doesn't have overlay data a blank copy of it is returned instead.
    '''    
    overlayData=Tag(0x60003000)
    overlayRows=Tag(0x60000010)
    overlayCols=Tag(0x60000011)
    overlayOrig=Tag(0x60000050)
    overlayType=Tag(0x60000040)
    overlayBits=Tag(0x60000100)

    tdesc,otype=image.tags.get(overlayType,(None,None))
    _,obits=image.tags.get(overlayBits,(None,None))
    
    out=image.clone()
    out.index=image.index
    out.tags=image.tags
    out.imageType=image.imageType
    out.isSpatial=True
    out.seriesID=image.seriesID
    out.img.fill(0)
    out.setMinMaxValues(0,0)
        
    if otype=='G' and obits==1:
        rows=int(image.tags[overlayRows][1])
        cols=int(image.tags[overlayCols][1])
        y,x=image.tags[overlayOrig][1]
        odat=image.tags[overlayData][1]
        
        dat=np.frombuffer(odat, dtype=np.uint8)
        dat=np.unpackbits(dat)[:rows*cols] # truncate padding
        dat=dat.reshape((-1,8)) # reshape to one byte's values per row
        dat=np.fliplr(dat) # flip byte order
        dat=dat.reshape((rows, cols)) # reshape to final
        
        out.img[y-1:y+rows,x-1:x+cols]=dat
        out.setMinMaxValues(dat.min(),dat.max())
        
    return out


def DicomSharedImage(filename,index=-1,isShared=False,rescale=True,dcm=None,includeTags=False):
    '''
    This pseudo-constructor creates a SharedImage object from a DICOM file. If `dcm' is None then the file is read
    from `filename', which must always be the valid path to the loaded DICOM, otherwise `dcm' must be the loaded Dicom
    object. The `index' value is for the ordering the caller imposes on a series of DICOM images, usually this is the 
    index of the image in its containing DICOM series. If `isShared' is True the image matrix is allocated in shared 
    memory. If `rescale' is True then the image data is rescaled according to the slope and intercept tags. The `timestep'
    value of the returned object is defined by the TriggerTime tag or inferred from the image comment if not present.
    
    Additional members are defined for the returned SharedImage object:
        * seriesID: string of the SeriesInstanceUID tag value or ''
        * imageType: string of the ImageType tag
        * isSpatial: is True if there's a valid pixel array and image position/orientation tags
        * isCompressed: True if the image data is compressed in a way which can't be read
        * tags: a dictionary of the Dicom tags taken from the loaded file if `includeTags' is True, {} otherwise
    '''
    dcm=read_file(filename) if dcm is None else dcm
    assert dcm!=None
    
    position=vec3(*roundHeaderVals(*dcm.get(positionTag,[0,0,0]))) # top-left corner
    dimensions=(dcm.get(colsTag,0),dcm.get(rowsTag,0))
    spacing=list(map(float,dcm.get(spacingTag,[1,1])))

    a,b,c,d,e,f=roundHeaderVals(*dcm.get(orientationTag,[1,0,0,0,-1,0]))
    orientation=rotator(vec3(a,b,c).norm(),vec3(d,e,f).norm(),vec3(1,0,0),vec3(0,-1,0))
    
    si=SharedImage(filename,position,orientation,dimensions,spacing)

    try:
        validPixelArray=dcm.pixel_array is not None
    except:
        validPixelArray=False

    si.index=index
    # extract Dicom properties of interest
    si.seriesID=str(dcm.get(seriesTag,''))
    si.imageType=list(dcm.get('ImageType',[]))
    si.isSpatial=validPixelArray and positionTag in dcm and orientationTag in dcm
    si.timestep=readDicomTimeValue(dcm) 
    si.isCompressed=not validPixelArray and not getattr(dcm,'_is_uncompressed_transfer_syntax',lambda:False)()
    si.tags=convertToDict(dcm) if includeTags else {}

    #if 0<=si.timestep<2: # convert from seconds to milliseconds
    #    si.timestep*=1000

    if validPixelArray:
        #wincenter=dcm.get('WindowCenter',None)
        #winwidth=dcm.get('WindowWidth',None)
        rslope=float(dcm.get(slopeTag,1) or 1)
        rinter=float(dcm.get(interTag,0) or 0)
        #rtype=dcm.get('RescaleType',None)

        # TODO: proper rescaling?
        if not rescale or rslope==0: 
            rslope=1.0
            rinter=0.0
            
        pixelarray=dcm.pixel_array
#        pixelarray=pixelarray*rslope+rinter # linux concurrency hang?
        
        if pixelarray.ndim==3: # TODO: handle actual multichannel images?
            pixelarray=np.sum(pixelarray,axis=2)

        si.allocateImg(si.seriesID+str(si.index),isShared)
        np.asarray(si.img)[:,:]=pixelarray # pixelarray is in (row,column) index order already
        si.img.mul(rslope)
        si.img.add(rinter)
        si.setMinMaxValues(*eidolon.minmaxMatrixReal(si.img))

    return si


class SeriesPropertyWidget(QtWidgets.QWidget,Ui_SeriesProp):
    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self,parent)
        self.setupUi(self)


class ChooseSeriesDialog(QtWidgets.QDialog,Ui_ChooseSeriesDialog):
    def __init__(self,plugin,resultf,dirpath=None,parent=None,allowMultiple=True,params=None,subject=None):
        QtWidgets.QDialog.__init__(self,parent)
        self.setupUi(self)
        self.plugin=plugin
        self.mgr=plugin.mgr
        self.dirpath=None
        self.resultf=resultf
        self.dds=None
        self.allowMultiple=allowMultiple
        self.params=params

        if subject:
            self.subject=subject
        else:
            self.subject='DICOM'

        self.setWindowTitle('Choose %s Series'%self.subject)

        self.chooseDirButton.clicked.connect(self._chooseDir)

        selmode=QtWidgets.QAbstractItemView.MultiSelection if allowMultiple else QtWidgets.QAbstractItemView.SingleSelection
        self.seriesList.setSelectionMode(selmode)

        if params!=None: # create the parameters panel and put it in the group box
            panel=eidolon.ParamPanel(params[0])
            panel.setParamChangeFunc(params[1])
            self.paramGroup.layout().addWidget(panel)
        else:
            self.paramGroup.setVisible(False) # hide the group box if no parameters are given

        if dirpath!=None:
            self._setDir(dirpath)
        else:
            self._chooseDir()

    def _chooseDir(self):
        dirpath=self.plugin.win.chooseDirDialog('Choose %s Directory'%self.subject)
        if os.path.isdir(dirpath):
            self._setDir(dirpath)

    def _setDir(self,dirpath):
        self.dirpath=dirpath
        self.dirEdit.setText(os.path.abspath(dirpath))
        fillList(self.seriesList,['Loading Directory, please wait'])
        f=self.plugin.loadDirDataset(dirpath)
        self._setDataset(f)

    @taskmethod('Filling list')
    def _setDataset(self,dds,task=None):
        self.dds=Future.get(dds)
        series=[]
        curitem=None

        if self.dds is not None and len(self.dds.series)>0:
            series=list(map(str,self.dds.series))
            if self.allowMultiple:
                curitem=0

        self.mgr.callThreadSafe(fillList,self.seriesList,series or ['No Dicom Files Found'],curitem=curitem)

    def accept(self):
        selected=[]
        for i in self.seriesList.selectedItems():
            ind=self.seriesList.indexFromItem(i)
            if ind.row()<len(self.dds.series):
                selected.append(self.dds.series[ind.row()])

        self.resultf.setObject(selected)
        self.done(1)

    def reject(self):
        self.resultf.setObject([])
        self.done(0)


class TimeMultiSeriesDialog(QtWidgets.QDialog,BaseCamera2DWidget,Ui_Dicom2DView):
    PreviewState=namedtuple('PreviewState','stackStart stackEnd minx miny maxx maxy')

    def __init__(self,serieslist,resultf,mgr,plugin,parent=None):
        assert eidolon.isMainThread()
        assert len(serieslist)>0
        QtWidgets.QDialog.__init__(self,parent)
        BaseCamera2DWidget.__init__(self,mgr,mgr.createCamera(isSecondary=True))
        self.setupUi(self)
        self.modifyDrawWidget(self.drawWidget)
        self.resultf=resultf
        self.plugin=plugin
        self.serieslist=list(serieslist)
        self.numImgs=min(len(s.filenames) for s in serieslist)
        self.simg=None # SharedImage object of the current image
        self.imgwidth=0
        self.imgheight=0
        self.tex=None # Texture for the current image

        # image data plane figure and material
        self.texmat=self.createMaterial('texmat')
        self.imgfig=self.getObjFigures('imgfig')[1][0]
        self.imgfig.setMaterial(self.texmat)

        self._setTexture() # initializes self.simg and self.tex

        self.recthandle=eidolon.RectHandle2D(self,[vec3(),vec3(1,0),vec3(0,1),vec3(1,1)],color(1,1,0))
        self.addHandle(self.recthandle)
        self._setHandle(10,10,self.imgwidth-10,self.imgheight-10)

        self.state=TimeMultiSeriesDialog.PreviewState(0,self.numImgs-1,0,0,self.imgwidth,self.imgheight)
        self.stateStack=[]

        # UI init
        fillList(self.seriesListWidget,[s.desc for s in self.serieslist])
        self.imgSlider.setRange(0,self.numImgs-1)
        self.imgNumBox.setRange(0,self.numImgs-1)
        self.minXBox.setRange(0,self.simg.dimensions[0]-1)
        self.maxXBox.setRange(0,self.simg.dimensions[0]-1)
        self.minYBox.setRange(0,self.simg.dimensions[1]-1)
        self.maxYBox.setRange(0,self.simg.dimensions[1]-1)
        self.imgStartBox.setRange(0,self.numImgs-1)
        self.imgEndBox.setRange(0,self.numImgs-1)

        self.imgEndBox.setValue(self.numImgs-1)
        self.maxXBox.setValue(self.imgwidth)
        self.maxYBox.setValue(self.imgheight)

        self.imgSlider.valueChanged.connect(self._selectImg)
        self.imgNumBox.valueChanged.connect(self._selectImg)

        self.seriesListWidget.itemSelectionChanged.connect(self._setTexture)
        self.seriesListWidget.model().layoutChanged.connect(self._reorderSeries)

        self._setOrderedBoxes(self.imgStartBox,self.imgEndBox)
        self._setOrderedBoxes(self.minXBox,self.maxXBox)
        self._setOrderedBoxes(self.minYBox,self.maxYBox)

        self.setStartButton.clicked.connect(lambda:self.imgStartBox.setValue(self.imgNumBox.value()))
        self.setEndButton.clicked.connect(lambda:self.imgEndBox.setValue(self.imgNumBox.value()))

        self.buttonBox.accepted.connect(self.createImage)
        self.buttonBox.rejected.connect(self.reject)

    def _worldToImgXY(self,x,y):
        return vec3(x+self.imgwidth/2,self.imgheight/2-y)

    def _imgToWorldXY(self,x,y):
        return vec3(x-self.imgwidth/2,self.imgheight/2-y)

    def _setBox(self,minx,maxx,miny,maxy):
        if minx<maxx and miny<maxy:
            minx=clamp(minx,0,self.imgwidth)
            maxx=clamp(maxx,0,self.imgwidth)
            miny=clamp(miny,0,self.imgheight)
            maxy=clamp(maxy,0,self.imgheight)

            self.minXBox.setValue(minx)
            self.maxXBox.setValue(maxx)
            self.minYBox.setValue(miny)
            self.maxYBox.setValue(maxy)
            self._setHandle(minx,miny,maxx,maxy)

    def _updateState(self,_=None):
        start=self.imgStartBox.value()
        end=self.imgEndBox.value()
        minx=self.minXBox.value()
        miny=self.minYBox.value()
        maxx=self.maxXBox.value()
        maxy=self.maxYBox.value()

        self._setHandle(minx,miny,maxx,maxy)
        self.state=TimeMultiSeriesDialog.PreviewState(start,end,minx,miny,maxx,maxy)
        self._repaintDelay()

    def _setHandle(self,nx,ny,xx,xy):
        self.recthandle.pts=list(itertools.starmap(self._imgToWorldXY,[(nx,ny),(xx,ny),(nx,xy),(xx,xy)]))

    def _setOrderedBoxes(self,minbox,maxbox):
        minbox.valueChanged.connect(lambda i:maxbox.setMinimum(min(i+1,maxbox.maximum())))
        maxbox.valueChanged.connect(lambda i:minbox.setMaximum(max(i-1,minbox.minimum())))
        minbox.valueChanged.connect(self._updateState)
        maxbox.valueChanged.connect(self._updateState)

    def _setTexture(self):
        self.simg=self._loadImage()
        w,h=self.simg.dimensions
        if self.tex==None: # if texture is None, create it and fill the figure with mesh data to represent the image
            self.tex=self.createTexture('imgtex',w,h,eidolon.TF_ALPHALUM8)
            self.texmat.setTexture(self.tex)
            self.imgwidth=w
            self.imgheight=h

            nodes,inds,xis=BaseCamera2DWidget.defaultQuad
            nodes=[vec3(w,h)*n for n in nodes]
            vb=eidolon.PyVertexBuffer(nodes,[vec3(0,0,1)]*len(nodes),None,xis)
            ib=eidolon.PyIndexBuffer(inds)
            self.imgfig.fillData(vb,ib)
            self.sceneBB=eidolon.BoundBox(nodes)

        if w>0 and h>0 and self.simg.img:
            assert (w,h)==(self.imgwidth,self.imgheight),'(%r,%r)!=(%r,%r)'%(w,h,self.imgwidth,self.imgheight)
            self.tex.fillColor(self.simg.img,0,self.simg.imgmin*2-self.simg.imgmax,self.simg.imgmax)
            self._repaintDelay()

    def _loadImage(self):
        seriesindex=self.seriesListWidget.currentRow()
        imgindex=self.imgNumBox.value()

        return self.serieslist[seriesindex].loadSharedImage(imgindex)

    def _selectImg(self,val=None):
        if val==None: # val is not None when the signal is from the slider, use the value in that case
            val=self.imgNumBox.value()

        with eidolon.signalBlocker(self.imgSlider,self.imgNumBox):
            self.imgSlider.setValue(val)
            self.imgNumBox.setValue(val)

        self._setTexture()

    def _reorderSeries(self):
        newlist=[]
        for w in self.seriesListWidget.findItems('*',Qt.MatchWrap|Qt.MatchWildcard):
            desc=str(w.text())
            series=first(s for s in self.serieslist if s.desc==desc)
            assert series
            newlist.append(series)

        self.serieslist=newlist
        self._setTexture()

    def updateView(self):
        start,end,minx,miny,maxx,maxy=self.state
        current=self.imgNumBox.value()

        minv,maxv=self.recthandle.getMinMax()
        minx,miny,_=self._worldToImgXY(minv.x(),minv.y())
        maxx,maxy,_=self._worldToImgXY(maxv.x(),maxv.y())
        self._setBox(min(minx,maxx),max(minx,maxx),min(miny,maxy),max(miny,maxy))

        self.recthandle.boxcol=color(0,1,0) if start<=current<=end else color(1,0,0)
        self.recthandle.updateHandle()

        #self._updateHandles(self.viewplane)
        #BaseCamera2DWidget.updateView(self)
        self.setFigTransforms()

    def createImage(self):
        @taskroutine('Loading Multiseries Image')
        def _load(task=None):
            with self.resultf:
                firstname=self.serieslist[0].desc
                lastname=self.serieslist[-1].desc
                name='%sto%s'%(firstname,lastname) if firstname!=lastname else firstname
                name=self.mgr.getUniqueObjName(eidolon.getValidFilename(name))
                images=[]
                start,end,minx,miny,maxx,maxy=self.state
                selection=list(range(start,end+1))
                crop=(minx,miny,maxx,maxy)

                for i,series in enumerate(self.serieslist):
                    self.plugin.loadSeriesImages(series,selection,False,crop)
                    images+=series.simgs
                    tslist=set(s.timestep for s in simgs)
                    
                    if len(tslist)==1 and first(tslist)<=eidolon.epsilon:
                    #if simgs[0].timestep==-1:
                        for s in simgs:
                            s.timestep=i

                self.resultf.setObject(ImageSceneObject(name,self.serieslist[0],images,self.plugin))

        self.mgr.runTasks(_load())
        self.accept()

    def reject(self):
        self.resultf.setObject(None)
        QtWidgets.QDialog.reject(self)


class DicomSeries(object):
    '''Represent a list of Dicom images which are members of a series. Changing will break existing .pickle files.'''
    def __init__(self,parent,seriesID,filenames=[],seriesNum=0,desc=''):
        self.parent=parent
        self.seriesID=seriesID
        self.seriesNum=seriesNum
        self.desc=desc
        self.filenames=list(filenames)
        self.simgs=[] #[None]*len(filenames) # initially empty list of ShareImage objects which will be loaded from Dicoms
        #self.tagmap=OrderedDict()
#       self.lastLoadArgs=() # last arguments used when loading images, pair of (selection,crop) values
#       self.selectCrop=None # (selection range, crop value) pair indicating the loading parameters used

    def getPropTuples(self):
        return [
            ('Series ID',self.seriesID),
            ('Series #',str(self.seriesNum)),
            ('Description',self.desc),
            ('# Images',str(len(self.filenames)))
        ]

    def getDatasetMap(self):
        '''Returns a dictionary containing the members of the object to store in a digest file.'''
        return {
            'seriesNum':self.seriesNum,
            'desc': self.desc,
            'filenames':self.filenames
        }

    def addFile(self,filename):
        if filename not in self.filenames:
            self.filenames.append(filename)
            #self.simgs.append(None)

    def addSharedImages(self,images):
        self.simgs+=images
#       for img in images:
#           ind=first(ind for ind,f in enumerate(self.filenames) if img.filename.endswith(f))
#           assert ind!=None,'%r not in %r'%(img.filename,self.filenames)
#           self.simgs[ind]=img
#           self.tagmap

    def getSharedImage(self,filename):
        return first(s for s in self.simgs if s and s.filename.endswith(filename))

    def clearSharedImages(self):
        del self.simgs[:]

    def enumFilePaths(self):
        for f in self.filenames:
            yield os.path.join(self.parent.rootdir,f)

    def loadDicomFile(self,index):
        return read_file(os.path.join(self.parent.rootdir,self.filenames[index]))

    def loadSharedImage(self,index):
        return DicomSharedImage(os.path.join(self.parent.rootdir,self.filenames[index]),index)

    def __repr__(self):
        return 'DicomSeries<%s, Series #: %i, # Images: %i>' % (self.desc,self.seriesNum,len(self.filenames))

    def __str__(self):
        return '%s %i [%i Files]' % (self.desc,self.seriesNum,len(self.filenames))


class DicomDataset(object):
    '''Represents all the loaded Dicom information for files found in a given root directory. Changing breaks .pickle files.'''
    def __init__(self,rootdir='.'):
        self.series=[]
        self.rootdir=rootdir

    def getSeries(self,seriesID,createNew=False):
        '''
        Get the series with the given ID `seriesID'. If no such series is present, create a new series object if
        `createNew' is True and return that, otherwise return None.
        '''
        seriesID=str(seriesID)

        s=first(s for s in self.series if s.seriesID==seriesID)
        if s is None and createNew:
            s=DicomSeries(self,seriesID)
            self.series.append(s)

        return s

    def findSeries(self,desc_or_func):
        '''
        Return the series which matches the criterion `desc_or_func'. If this is a string then return the first series
        which contains it in its description. If not a string, it's assumed to be a callable returning True when the
        desired series object is given as the sole argument.
        '''
        if isinstance(desc_or_func,str):
            func=lambda s:desc_or_func in s.desc
        else:
            func=desc_or_func

        return first(s for s in self.series if func(s))

    def getDatasetMap(self):
        '''
        Returns a dictionary containing the condensed information for this dataset. The `rootdir' value is keyed
        to itself, and there is a list of series IDs keyed to `series'. Each series object in self.series is also
        keyed to its series ID in the result.
        '''
        result={
            'rootdir':self.rootdir,
            'series':[s.seriesID for s in self.series]
        }

        for s in self.series:
            result[s.seriesID]=s.getDatasetMap()

        return result

    def storeDataset(self,filename):
        '''Store the dataset dictionary to the basic config file `filename'.'''
        eidolon.storeBasicConfig(filename,self.getDatasetMap())

    def loadDataset(self,filename):
        '''Load data into the dataset from the basic config file `filename' which was created with storeDataset().'''
        dsmap=eidolon.readBasicConfig(filename)

        # check that the root directory makes sense
        # TODO: not actually needed? If the whole directory is moved the root will be different but file paths relative to the digest file will be correct
        #if not isSameFile(self.rootdir,dsmap['rootdir']) or not os.path.isdir(dsmap['rootdir']):
        #   raise ValueError('Digest file root directory %r not valid'%dsmap['rootdir'])

        for sid in dsmap['series']:
            series=DicomSeries(self,sid,**dsmap[sid])
            self.series.append(series)

            # ensure the files referred to by the series still exist
            if any(not os.path.isfile(f) for f in series.enumFilePaths()):
                raise ValueError('Series %r out of sync with filesystem'%sid)

    def addDataset(self,dds):
        '''Merge the dataset `dds' into this one, assuming both have the same root directory.'''
        assert dds.rootdir==self.rootdir

        for s in dds.series:
            ss=self.getSeries(s.seriesID,True)
            if len(ss.desc)==0:
                ss.desc=s.desc
                ss.seriesNum=s.seriesNum

            for f in s.filenames:
                ss.addFile(f)

    def __str__(self):
        return 'Dataset %s #Images %i' %(self.rootdir,sum(len(s.filenames) for s in self.series))
    

class DicomPlugin(ImageScenePlugin):
    def __init__(self):
        ImageScenePlugin.__init__(self,'Dicom')
        self.dirobjs={}
        self.loadedNames=[]
        self.selectCropMap={} # maps series to image selection/crop pairs

    def init(self,plugid,win,mgr):
        ImageScenePlugin.init(self,plugid,win,mgr)
        if win:
            win.addMenuItem('Import','DicomLoad'+str(plugid),'&Dicom Directory',self._openDicomDirMenuItem)
            win.addMenuItem('Import','DicomVLoad'+str(plugid),'&Dicom Volume File',self._openVolumeMenuItem)
            win.addMenuItem('Export','DicomExport'+str(plugid),'&Dicom Files',self._exportMenuItem)

            # if the dicomdir argument is given open up the series load dialog with the given directory (or current directory if not given)
            if mgr.conf.hasValue('args','--dicomdir'):
                dicomdir=mgr.conf.get('args','--dicomdir')
                if dicomdir=='--dicomdir':
                    dicomdir='.'

                # add a task which will call loadDicomDir() asynchronously so that the task queue is freed for dicom loading
                mgr.addFuncTask(lambda:eidolon.asyncfunc(self.loadDicomDir)(dicomdir))

    def getHelp(self):
        return '\nUsage: --dicomdir[=scan-dir-path]'
    
    def getDatasets(self):
        return list(self.dirobjs.values())

    def enumSeries(self):
        for dds in self.getDatasets():
            for s in dds.series:
                yield s

    @taskmethod('Loading Image Data')
    @timing
    def loadSeriesImages(self,series,selection,crop=None,task=None):
        '''Load the actual image data from the files in `series' and store them as SharedImage objects in series.simgs.'''
        
        # look for the series if `series' is a string 
        if isinstance(series,str):
            allseries=eidolon.listSum(dds.series for dds in self.dirobjs.values())
            series1=first(s for s in allseries if s.seriesID==series)
            assert series1!=None,'Cannot find series %r'%series
            series=series1

        assert len(series.filenames)>0
        assert selection==None or all(s<len(series.filenames) for s in selection)

        if len(series.filenames)>0:
            proccount=eidolon.chooseProcCount(len(series.filenames),0,10)
            rootdir=series.parent.rootdir

            if self.selectCropMap.get(series,None)!=(selection,crop):
                series.clearSharedImages()

            self.selectCropMap[series]=(selection,crop)

            # get the series filenames or a selected range thereof if `selection' is given
            filenames=[series.filenames[i] for i in selection] if selection else series.filenames
            # remove already-loaded images
            filenames=[i for i in filenames if series.getSharedImage(i)==None]

            if len(filenames)>0:
                simgs=loadSharedImages(len(filenames),proccount,task,rootdir,filenames,crop,partitionArgs=(filenames,))
                eidolon.checkResultMap(simgs)
                series.addSharedImages(eidolon.sumResultMap(simgs)) # add new images, there isn't necessarily any order to this list

        return series

    def loadSeries(self,series,name=None,selection=None,loadSequential=False,isTimeDependent=None,crop=None):
        '''Loads the Dicom files for the given series object or series ID string `series' into a SceneObject subtype.'''
        f=Future()

        ff=self.loadSeriesImages(series,selection,crop)
        self.mgr.checkFutureResult(ff)

        @taskroutine('Creating Scene Object')
        def createDicomObject(name,task):
            with f:
                series=Future.get(ff)
                # choose a unique name, based on the given name or the series description
                name=eidolon.uniqueStr(name or series.desc,[o.getName() for o in self.mgr.enumSceneObjects()]+self.loadedNames)
                self.loadedNames.append(name)
                
                sel=selection or list(range(len(series.filenames)))
                imgs=[series.getSharedImage(series.filenames[i]) for i in sel]
                assert len(imgs)>0
                assert any(i!=None for i in imgs)

                hasCompressed=any(i.isCompressed for i in imgs if i)
                imgs=[i for i in imgs if i!=None and i.img!=None] # remove unfound images

                if len(imgs)==0:
                    if hasCompressed:
                        raise IOError('Series %r contained compressed images DicomPlugin cannot decompress'%name)
                    else:
                        raise IOError('Empty series %r; no Dicom files found or Dicom files are not readable'%name)

                obj=ImageSceneObject(name,series,imgs,self,isTimeDependent)
                
                # convert from seconds to milliseconds, assumes MR/CT capture rates that are never faster than a millisecond
                if avgspan(obj.getTimestepList())<1:
                    for i in obj.images:
                        i.timestep*=1000.0

                f.setObject(obj)

        return self.mgr.runTasks([createDicomObject(name)],f,loadSequential)

    @timing
    def loadDigestFile(self,dirpath,task):
        '''
        Loads the directory digest ini file in 'dirpath' if it exists, or creates it otherwise. Returns the loaded
        or created DicomDataset object.
        '''
        dirpath=os.path.abspath(dirpath)
        dirfiles=list(eidolon.enumAllFiles(dirpath))
        picklefile=os.path.join(dirpath,'dicomdataset.pickle')
        digestfile=os.path.join(dirpath,digestFilename)
        useDigestFile=False

        # delete legacy pickle file
        if os.path.isfile(picklefile):
            os.remove(picklefile)

        # if the digest file exists and is later than all the files in the directory, set useDigestFile to True
        if os.path.isfile(digestfile):
            digeststat=os.stat(digestfile)
            useDigestFile=all(os.stat(f).st_mtime<=digeststat.st_mtime for f in dirfiles)

        # if the digest file is present and later than the other files, try to load it
        if useDigestFile:
            try:
                ds=DicomDataset(dirpath)
                ds.loadDataset(digestfile)
            except:
                useDigestFile=False # digest file was bogus somehow, load the hard way

        # if the digest file wasn't present or failed to load, create the dataset object by scanning the directory then try to save the digest
        if not useDigestFile:
            ds=DicomDataset(dirpath)

            proccount=eidolon.chooseProcCount(len(dirfiles),0,500)
            ddsmap=createDicomDatasets(len(dirfiles),proccount,task,dirpath,dirfiles,partitionArgs=(dirfiles,))

            for dds in ddsmap.values():
                ds.addDataset(dds)

            # try to store the digest file but if it fails (ie. read-only filesystem) just continue since it's only an optimization
            try:
                ds.storeDataset(digestfile)
            except:
                pass

        return ds

    @taskmethod('Loading Dicom Directory')
    def loadDirDataset(self,dirpath,task=None):
        '''Loads the dataset directory as an asset and creates the DicomDataset object keyed to `dirpath' in self.dirobjs.'''
        
        if dirpath in self.dirobjs:
            return self.dirobjs[dirpath]
        
        # load the directory dataset object if it isn't already loaded
        dds=self.loadDigestFile(dirpath,task)
        self.dirobjs[dirpath]=dds

        # add the dataset as an asset to the UI
        if self.win:
            self.win.addAsset(dds,dirpath,eidolon.AssetType._dcm)
            self.win.sync()
            listitem=self.win.findWidgetItem(dds)
    
            # add each series as a child of the dataset asset item
            for s in dds.series:
                prop=self.mgr.callThreadSafe(SeriesPropertyWidget)
                self.win.addAsset(s,str(s),eidolon.AssetType._dcm,prop,self._updateSeriesPropBox)
                self.win.sync()
                slistitem=self.win.findWidgetItem(s)
                # reset the list item's parent by removing it and adding it to the new paren't child list
                slistitem.parent().removeChild(slistitem)
                listitem.addChild(slistitem)
    
                # double lambda needed to capture local variables 'prop' and 's'
                caplambda=lambda prop,ss: lambda:self._loadSeriesButton(prop,ss)
                self.win.connect(prop.createButton.clicked,caplambda(prop,s))
    
            listitem.setExpanded(True) # expand th list of series

        return dds

    def acceptFile(self,filename):
        try:
            read_file(filename) # attempt to read as a Dicom, file extensions aren't always present so this is necessary
            return True
        except:
            return False

    def loadObject(self,filename,name=None,*args,**kwargs):
        dcm=read_file(filename)

        if str(dcm.Modality)=='US' and NonstandardTags.USpixeldata in dcm: # ultrasound volume
            return self.loadDicomVolume(filename,name,*args,**kwargs)
        else:
            # load the directory the file is in then load the series the file was from
            seriesID=str(dcm.get('SeriesInstanceUID',''))
            self.loadDirDataset(os.path.dirname(filename))
            return self.loadSeries(seriesID,name)

    @taskmethod('Loading Volume File')
    def loadDicomVolume(self,filename,name=None,interval=1.0,toffset=0.0,position=vec3(),rot=rotator(),task=None):
        '''Load a single DICOM file containing a 3D or 4D image volume (ie. ultrasound) using nonstandard tags.'''
        dcm=read_file(filename)
        name=name or eidolon.splitPathExt(filename)[1]

        NT=NonstandardTags
        spacing=vec3(dcm[NT.USpixdimx].value,dcm[NT.USpixdimy].value,dcm[NT.USpixdimz].value)*10
        dimsize=(dcm[NT.USnumframes].value,dcm[NT.USdepth].value,dcm[NT.USheight].value,dcm[NT.USwidth].value)
        pixeldata=dcm[NT.USpixeldata].value

        assert len(pixeldata)==eidolon.prod(dimsize), 'Pixel data dimension is %i, should be %i'%(len(pixeldata),eidolon.prod(dimsize))

        dat=np.ndarray(dimsize,dtype=np.uint8,buffer=pixeldata,order='C')
        dat=np.transpose(dat,(3,2,1,0))

        obj=self.createObjectFromArray(name,dat,interval,toffset,position,rot*rotator(eidolon.halfpi,0,0),spacing,task=task)
        obj.source=convertToDict(dcm)
        return obj

    def saveImage(self,dirpath,obj,datasetTags={},fileMetaTags={}):
        '''Deprecated, for compatibility only.'''
        return self.saveObject(obj,dirpath,datasetTags=datasetTags,fileMetaTags=fileMetaTags)

    @taskmethod('Saving DICOM Files')
    def saveObject(self,obj,path,overwrite=False,setFilenames=False,datasetTags={},fileMetaTags={},task=None, *args,**kwargs):
        defaultfiletags={
            # TODO: are these correct? I'm just copy-pasting from http://stackoverflow.com/questions/14350675/create-pydicom-file-from-numpy-array
            'MediaStorageSOPClassUID' : '1.2.840.10008.5.1.4.1.1.7', # UID for SOP "Secondary Capture Image Storage", same as SOPClassUID
            'MediaStorageSOPInstanceUID' : '1.3.6.1.4.1.9590.100.1.1.111165684411017669021768385720736873780',
            'ImplementationClassUID' : '1.3.6.1.4.1.9590.100.1.0.100.4.0'
        }

        defaultdatasettags={
            'ContentDate' : str(datetime.date.today()).replace('-',''),
            'ContentTime' : str(time.time()),
            'Modality' : 'WSD',
            # TODO: are these correct UIDs?
            'SOPInstanceUID' : defaultfiletags['MediaStorageSOPInstanceUID'],
            'SOPClassUID' : defaultfiletags['MediaStorageSOPClassUID'], # UID for SOP "Secondary Capture Image Storage"
            # TODO: need to choose instance UIDs better
            'SeriesInstanceUID' : '1.3.6.1.4.1.9590.100.1.1.'+(''.join(str(randint(0,10)) for i in range(39))),
            'StudyInstanceUID' :  '1.3.6.1.4.1.9590.100.1.1.'+(''.join(str(randint(0,10)) for i in range(39))),
            'SecondaryCaptureDeviceManufctur' : sys.version,
            'SamplesPerPixel' : 1,
            'PhotometricInterpretation' : "MONOCHROME2",
            'PixelRepresentation' : 0,
            'HighBit' : 15,
            'BitsStored' : 16,
            'BitsAllocated' : 16,
            'RescaleSlope' : 1,
            'RescaleIntercept' : 0,
            'PatientName' : 'Anon',
            'SmallestImagePixelValue' : '\\x00\\x00', # these are both default values, the actual image contents may not reflect this
            'LargestImagePixelValue' : '\\xff\\xff',
            'SliceThickness': obj.getVoxelSize().z()
        }

        if not path: # if no path given, choose the one the first source file is in or the current directory
            files=obj.plugin.getObjFiles(obj)
            path=os.path.dirname(files[0]) if files else os.getcwd()

        rootpath=os.path.join(path,eidolon.getValidFilename(obj.getName()))
        dtype=np.uint16
        maxrange=np.iinfo(dtype).max-np.iinfo(dtype).min

        if task:
            task.setMaxProgress(len(obj.images))

        # write out each image in the order the object stores them, this should preserve order between Dicom import/export operations
        for index,image in enumerate(obj.images):
            if task:
                task.setProgress(index+1)

            filename='%s_%.5i.dcm'%(rootpath,index)

            # calculate intercept and slope
            intercept=image.imgmin
            imgrange=image.imgmax-intercept
            slope=max(1,imgrange/float(maxrange)) # slope is 1 if values are all within the range of dtype, otherwise is a scaling value

            # convert pixel array to the correct data type and scaling by slope/intercept
            pixel_array=((np.asarray(image.img)-intercept)/slope).astype(dtype)

            # create and fill in a dataset object the file requires
            file_meta = Dataset()
            metatags=list(defaultfiletags.items())+list(fileMetaTags.items())
            for k,v in metatags:
                setattr(file_meta,k,v)

            # create and fill in the file-specific dataset
            ds = FileDataset(filename, {},file_meta = file_meta,preamble="\0"*128)
            filetags=list(defaultdatasettags.items())+list(datasetTags.items())
            for k,v in filetags:
                setattr(ds,k,v)

            # set specific values for this image
            ds.RescaleSlope=slope
            ds.RescaleIntercept=intercept
            ds.Columns = pixel_array.shape[1]
            ds.Rows = pixel_array.shape[0]
            ds.ImagePositionPatient=list(image.position)
            ds.ImageOrientationPatient=list(image.orientation*vec3(1,0,0))+list(image.orientation*vec3(0,-1,0))
            ds.TriggerTime=int(image.timestep)
            ds.PixelSpacing=list(image.spacing)
            ds.SliceLocation=0#s*ds.SliceThickness
            ds.SeriesDescription=obj.getName()
            ds.PixelData = pixel_array.tostring()
            ds.SmallestImagePixelValue=pixel_array.min()
            ds.LargestImagePixelValue=pixel_array.max()

            ds.save_as(filename)

    def getScriptCode(self,obj,**kwargs):
        configSection=kwargs.get('configSection',False)
        namemap=kwargs.get('namemap',{})
        varname=namemap[obj] #[obj.getName()]
        script=''
        args={}

        if not configSection and isinstance(obj,ImageSceneObject):
            args={
                'varname':varname,
                'objname':obj.name,
                'series':obj.source.seriesID,
                'isTimeDep': obj.isTimeDependent
            }

            for i in self.dirobjs.keys():
                script+='Dicom.loadDirDataset(%r)\n' % os.path.normpath(i)

            if isinstance(obj.source,DicomSeries):
                indices=[i.index for i in obj.images]
                indices.sort()
                if indices==list(range(len(obj.images))):
                    indices=None

                args['indices']=indices

                script+='%(varname)s = Dicom.loadSeries(%(series)r,%(objname)r,%(indices)r,False,%(isTimeDep)r)\n'

        elif isinstance(obj,ImageSceneObjectRepr):
            args={
                'varname':varname,
                'pname':namemap[obj.parent],
                'reprtype':obj.reprtype,
                'matname':namemap.get(obj.getMaterialName(),'Greyscale')
            }

            if configSection:
                script= ImageScenePlugin.getScriptCode(self,obj,setMaterial=False,**kwargs)

                if isinstance(obj,eidolon.ImageVolumeRepr):
                    args['numplanes']=obj.getNumPlanes()
                    script+="%(varname)s.setNumPlanes(%(numplanes)r)\n"
            else:
                script= "%(varname)s=%(pname)s.createRepr(ReprType._%(reprtype)s,imgmat=%(matname)s)\n"

        return eidolon.setStrIndent(script % args).strip()+'\n'

    def showChooseSeriesDialog(self,dirpath=None,allowMultiple=True,params=None,subject=None):
        '''
        Opens a dialog for choosing a series to load. The starting directory is given by `dirpath', this path is used
        in the dialog, but if left as None an open directory dialog is presented for choosing one. If `allowMultiple'
        is true then multiple series can be returned. If `params' is a pair containing a list of ParamDef objects and
        a callable accepting 2 arguments, then a ParamPanel is created in the series choose dialog using the given
        callable as the callback for changed values. The `subject' parameter, if given, should be a string describing
        what is being chosen which is used in the dialog title. The method blocks so long as the dialog is open, and
        returns an iterable of zero or more DicomSeries objects once it is closed. Internally a task is create so this
        must not be called within a task but in a separate thread.
        '''
        f=Future()
        @self.mgr.callThreadSafe
        def showDialog():
            with f:
                d=ChooseSeriesDialog(self,f,dirpath,self.win,allowMultiple,params,subject)
                d.exec_()

        return f(None) # block since the result will be known once the dialog closes so there's nothing to do asynchronously

    def showTimeMultiSeriesDialog(self,series):
        '''
        Shows the multi-series dialog box for the given series list, returning the Future object which will contain the
        results from the user cropping and ordering the images of the series. This does block and is thread-safe.
        '''
        f=Future()
        @self.mgr.callThreadSafe
        def showDialog():
            with f:
                d=TimeMultiSeriesDialog(eidolon.toIterable(series),f,self.mgr,self,self.win)
                d.exec_()

        return f # do not block on f since data is loaded in a task and stored in f

    def loadDicomDir(self,dirpath=None,allowMultiple=True,params=None,subject=None):
        '''
        Shows the choose series dialog using the same arguments as showChooseSeriesDialog() then loads any selected
        series as ImageSceneObject instances. This will block so long as the dialog is open but otherwise will use
        tasks to load the data. It is thread-safe.
        '''
        series=self.showChooseSeriesDialog(dirpath,allowMultiple,params,subject)
        for s in series:
            self.mgr.addSceneObjectTask(self.loadSeries(s))

    def _openDicomDirMenuItem(self):
        self.loadDicomDir()

    def _openVolumeMenuItem(self):
        filename=self.win.chooseFileDialog('Choose Dicom filename')
        if filename:
            obj=self.loadDicomVolume(filename)
            self.mgr.addFuncTask(lambda:self.mgr.addSceneObject(obj),'Loading Dicom file')

    def _updateSeriesPropBox(self,series,prop):
        if prop.propTable.rowCount()==0:
            eidolon.fillTable(series.getPropTuples(),prop.propTable)

        if prop.lastBox.value()==0:
            prop.lastBox.setValue(len(series.filenames))

        prop.firstBox.setRange(0,len(series.filenames))
        prop.lastBox.setRange(1,len(series.filenames))
        prop.stepBox.setRange(0,len(series.filenames))

    def _loadSeriesButton(self,prop,series):
        firstind=int(prop.firstBox.value())
        lastind=int(prop.lastBox.value())
        stepind=int(prop.stepBox.value())

        if prop.selectedButton.isChecked():
            selectlist=list(range(len(series.filenames)))[firstind:lastind:stepind]
        else:
            selectlist=None

        obj=self.loadSeries(series,None,selectlist)
        self.mgr.addSceneObjectTask(obj)

    def _exportMenuItem(self):
        obj=self.win.getSelectedObject()
        if not isinstance(obj,(ImageSceneObject,ImageSceneObjectRepr)):
            self.mgr.showMsg('Error: Must select image data object to export','DICOM Export')
        else:
            if isinstance(obj,ImageSceneObjectRepr):
                obj=obj.parent

            outdir=self.win.chooseDirDialog('Choose directory to save Dicoms to')
            if outdir:
                f=self.saveObject(obj,outdir,overwrite=True)
                self.mgr.checkFutureResult(f)


### Add plugin to environment

eidolon.addPlugin(DicomPlugin())

### Unit tests

class TestDicomPlugin(unittest.TestCase):
    def setUp(self):
        self.tempdir=tempfile.mkdtemp()
        self.plugin=eidolon.getSceneMgr().getPlugin('Dicom')
        self.dcmdir=os.path.join(eidolon.getAppDir(),'tutorial','DicomData')
        
        self.vfunc=lambda x,y,z,t:(x+1)*1000+(y+1)*100+(z+1)*10+t+1
        self.volarr=np.fromfunction(np.vectorize(self.vfunc),(21,33,46,17))
        self.vpos=vec3(-10,20,-15)
        self.vrot=rotator(0.1,-0.2,0.13)

        self.vol=self.plugin.createObjectFromArray('TestVolume',self.volarr,pos=self.vpos,rot=self.vrot)
        
        self.pfunc= lambda x,y: 1 if np.prod((x,y))==0 else 0
        self.planearr=np.fromfunction(np.vectorize(self.pfunc),(12,13))
        self.plane=self.plugin.createObjectFromArray('TestPlane',self.planearr,pos=self.vpos,rot=self.vrot)
        
        
    def tearDown(self):
        shutil.rmtree(self.tempdir)
        
    def rotatorsEqual(self,r1,r2):
        r1=np.asarray(list(r1))
        r2=np.asarray(list(r2))
        
        return np.sum(np.abs(r1-r2))
        
    def testLoad(self):
        '''Test loading a dicom file from the tutorial directory.'''
        dcmfile=os.path.join(self.dcmdir,'SA_00000.dcm')
        dcm=DicomSharedImage(dcmfile)
        self.assertIsNotNone(dcm)
    
    def testLoadDigest(self):
        '''Test loading a digest file.'''
        digestfile=os.path.join(self.dcmdir,digestFilename)
        
        ds=self.plugin.loadDigestFile(self.dcmdir,None)
        
        self.assertIsNotNone(ds)
        self.assertTrue(os.path.isfile(digestfile))
        os.remove(digestfile)
    
    def testLoadDir(self):
        '''Test loading a directory containing Dicom files.'''
        digestfile=os.path.join(self.dcmdir,digestFilename)
        
        f=self.plugin.loadDirDataset(self.dcmdir)
        result=Future.get(f)
        
        self.assertIsNotNone(result)
        assert self.dcmdir in self.plugin.dirobjs, '%r not in %r'%(self.dcmdir,self.plugin.dirobjs)
        self.assertTrue(os.path.isfile(digestfile))
        os.remove(digestfile)
        
    def testSaveLoadPlane(self):
        self.plugin.saveObject(self.plane,self.tempdir)
        firstfile=first(glob.glob(self.tempdir+'/*'))
        read_file(firstfile)
        
        eidolon.printFlush(self.planearr)
        
#    def testSaveLoadVolume(self):
#        '''Test saving and loading a volume image with Dicom files.'''
#        self.plugin.saveObject(self.vol,self.tempdir)
#        firstfile=first(glob.glob(self.tempdir+'/*'))
#        
#        print(read_file(firstfile))
#        print(self.vol.images[0].imgmin,self.volarr[...,0].min())
#        
#        obj1=self.plugin.loadObject(firstfile)
#        trans=obj1.getVolumeTransform()
#        
#        self.assertEqual(self.vpos,trans.getTranslation())
#        self.assertTrue(self.rotatorsEqual(self.vrot,trans.getRotation()))
#        
#        self.assertEqual(self.vol.getArrayDims(),obj1.getArrayDims())
#        
#        with eidolon.processImageNp(obj1) as arr1:
#            self.assertEqual(self.volarr.shape,arr1.shape)
#            
#            diff=np.sum(np.abs(self.volarr-arr1))
#            self.assertAlmostEqual(diff,0,4,'%r is too large'%(diff,))
    