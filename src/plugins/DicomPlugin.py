# Eidolon Biomedical Framework
# Copyright (C) 2016-7 Eric Kerfoot, King's College London, all rights reserved
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

from eidolon import *

addLibraryFile('pydicom-1.0.0a1-py2.7') # PyDicom: https://github.com/darcymason/pydicom


from pydicom.dicomio import read_file
from pydicom.datadict import DicomDictionary
from pydicom.errors import InvalidDicomError
from pydicom.tag import Tag
from pydicom.dataset import Dataset,FileDataset
	
import os
import sys
import pickle
import threading
import mmap
import datetime
import time
from collections import OrderedDict
from Queue import Queue
from random import randint

import numpy as np

from ui.SeriesProp import Ui_ObjProp
from ui.ChooseSeries import Ui_ChooseSeriesDialog
from ui.Dicom2DView import Ui_Dicom2DView

AssetType.append('dcm','Dicom Sources','Dicom Datasets (Directory References)') # adds the DICOM directory asset type to the asset panel


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


keywordToTag={v[4]:(k>>16,k&0xffff) for k,v in DicomDictionary.items()} # maps tag keywords to 2 part tag numbers


headerPrecision=4 # precision of float values in DICOM headers, values are only correct to this number plus one of significant figures


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
	tag is present then this is used, otherwise attempt to parse the RR value from the "ImageComments" tag if this is
	present. The comment should be something like "RR 1153 +/- 41; 138 heartbeats" for this to work, in which case the
	first number is the average cycle time in ms. If no heart rate is found then return None.
	'''
	if isinstance(series_or_dcm,DicomSeries):
		dcm=series_or_dcm.loadDicomFile(0)
	else:
		dcm=series_or_dcm
		
	heartrate=dcm.get('HeartRate',None)

	# if the HeartRate tag isn't given attempt to parse the RR time from the comment field
	if not heartrate:
		comment=dcm.get('ImageComments','')
		if comment.startswith('RR'):
			heartrate=60000/int(comment.split()[1])
			
	return heartrate
	

def createDicomReadThread(rootpath,files,readPixels=True):
	'''
	Reads the Dicom files in `rootpath' listed by relative file names in the list  `files', and returns the reading
	thread object and the synchronized queue containing (relative-filenames,Dicom-object) pairs produced by the thread.
	'''
	dcmqueue=Queue()

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

			if len(series.desc)==0:
				series.desc=str(ds.get('SeriesDescription',series.desc)).strip()

			if series.seriesNum==0:
				series.seriesNum=int(ds.get('SeriesNumber',series.seriesNum))

			counter+=1
			process.setProgress(counter)
		except:
			pass

	return dds


@concurrent
def loadSharedImages(process,rootdir,files,crop=None):
	'''Reads the image data from the listed files and returns a list of SharedImage objects storing this image data.'''
	result=[]

	for i in range(len(files)):
		process.setProgress(i+1)
		try:
			filename=os.path.join(rootdir,files[i])
			dcm=DicomSharedImage(filename,i+process.startval,False)
			if crop!=None and (crop[0]>0 or crop[1]>0 or crop[2]<dcm.dimensions[0]-1 or crop[3]<dcm.dimensions[1]-1):
				dcm=dcm.crop(*crop)

			dcm.setShared(True)
			result.append(dcm)
		except TypeError as te:
			printFlush(te)
			#pass # ignore Dicoms that don't have pixel information

	return result
	
	
def convertToDict(dcm):
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
			if not isPicklable(value):
				value=str(value)

		return value

	return _datasetToDict(dcm)
	
	
def addDicomTagsToMap(dcm,tagmap):
	def _elemToValue(elem):
		value=None
		if elem.VR=='SQ':
			value=OrderedDict()
			for i,item in enumerate(elem):
				value['item_%i'%i]=_datasetToDict(item)
		elif elem.name!='Pixel Data':
			value=elem.value
			if not isPicklable(value):
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
				
				
def isPhaseImage(image):
	'''Returns True if the SharedImage or Dicom image object `image' has a tag field indicating the image is phase.'''
	imagetype=list(getattr(image,'imageType',None) or image.get('ImageType',[])) # imageType in SharedImage, ImageType in Dicom
	
	# these are the members of imagetype which should indicate phase image for the different manufacturers
	# (see https://uk.mathworks.com/matlabcentral/fileexchange/31978-readdicomdir-indir-debuglevel-reply-/content/ReadDicomDir.m)
	phasevalue1='PHASE MAP' # philips?
	phasevalue2='P' # Siemens?
	
	return phasevalue1 in imagetype or phasevalue2 in imagetype
			

class SeriesPropertyWidget(QtGui.QWidget,Ui_ObjProp):
	def __init__(self, parent=None):
		QtGui.QWidget.__init__(self,parent)
		self.setupUi(self)


class ChooseSeriesDialog(QtGui.QDialog,Ui_ChooseSeriesDialog):
	def __init__(self,plugin,resultf,dirpath=None,parent=None,allowMultiple=True,params=None,subject=None):
		QtGui.QDialog.__init__(self,parent)
		self.setupUi(self)
		self.plugin=plugin
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

		selmode=QtGui.QAbstractItemView.MultiSelection if allowMultiple else QtGui.QAbstractItemView.SingleSelection
		self.seriesList.setSelectionMode(selmode)

		if params!=None: # create the parameters panel and put it in the group box
			panel=ParamPanel(params[0])
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
		self.plugin.mgr.addFuncTask(lambda:self.plugin.mgr.callThreadSafe(self._setDataset,f()))

	def _setDataset(self,dds):
		self.dds=dds
		if dds==None or len(dds.series)==0:
			fillList(self.seriesList,['No DICOM series found'])
		else:
			fillList(self.seriesList,map(str,dds.series),curitem=(0 if not self.allowMultiple else None))

	def accept(self):
		selected=[]
		for i in self.seriesList.selectedItems():
			ind=self.seriesList.indexFromItem(i)
			selected.append(self.dds.series[ind.row()])

		self.resultf.setObject(selected)
		self.done(1)

	def reject(self):
		self.resultf.setObject([])
		self.done(0)


class TimeMultiSeriesDialog(QtGui.QDialog,BaseCamera2DWidget,Ui_Dicom2DView):
	PreviewState=collections.namedtuple('PreviewState','stackStart stackEnd minx miny maxx maxy')

	def __init__(self,serieslist,resultf,mgr,plugin,parent=None):
		assert isMainThread()
		assert len(serieslist)>0
		QtGui.QDialog.__init__(self,parent)
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

		self.recthandle=RectHandle2D(self,[vec3(),vec3(1,0),vec3(0,1),vec3(1,1)],color(1,1,0))
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
			self.tex=self.createTexture('imgtex',w,h,TF_ALPHALUM8)
			self.texmat.setTexture(self.tex)
			self.imgwidth=w
			self.imgheight=h

			nodes,inds,xis=BaseCamera2DWidget.defaultQuad
			nodes=[vec3(w,h)*n for n in nodes]
			vb=PyVertexBuffer(nodes,[vec3(0,0,1)]*len(nodes),None,xis)
			ib=PyIndexBuffer(inds)
			self.imgfig.fillData(vb,ib)
			self.sceneBB=BoundBox(nodes)

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

		with signalBlocker(self.imgSlider,self.imgNumBox):
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
				images=[]
				name=getValidFilename('%sto%s'%(self.serieslist[0].desc,self.serieslist[-1].desc))
				start,end,minx,miny,maxx,maxy=self.state
				selection=range(start,end+1)
				crop=(minx,miny,maxx,maxy)
				for i,series in enumerate(self.serieslist):
					simgs=self.plugin.loadSeriesImages(series,selection,False,crop)
					images+=simgs
					if simgs[0].timestep==-1:
						for s in simgs:
							s.timestep=i

				self.resultf.setObject(ImageSceneObject(name,self.serieslist[0],images,self.plugin,len(self.serieslist)>1))

		self.mgr.runTasks(_load())
		self.accept()

	def reject(self):
		self.resultf.setObject(None)
		QtGui.QDialog.reject(self)


def DicomSharedImage(filename,index,isShared=True,rescale=True,dcm=None):
	'''
	This pseudo-constructor creates a SharedImage object from a DICOM file. If `dcm' is None then the file is read
	from `filename', which must always be the valid path to the loaded DICOM. The `index' value is for the ordering the
	caller imposes on a series of DICOM images, usually this is the index of the image in its containing DICOM series.
	'''
	dcm=dcm or read_file(filename)
	assert dcm!=None

	position=vec3(*roundHeaderVals(*dcm.get('ImagePositionPatient',[0,0,0]))) # top-left corner
	dimensions=(dcm.get('Columns',0),dcm.get('Rows',0))
	spacing=map(float,dcm.get('PixelSpacing',[1,1]))

	a,b,c,d,e,f=roundHeaderVals(*dcm.get('ImageOrientationPatient',[1,0,0,0,-1,0]))
	orientation=rotator(vec3(a,b,c).norm(),vec3(d,e,f).norm(),vec3(1,0,0),vec3(0,-1,0))
	
	si=SharedImage(filename,position,orientation,dimensions,spacing)

	try:
		validPixelArray=dcm.pixel_array is not None
	except:
		validPixelArray=False

	si.index=index
	
	# extract Dicom properties of interest
	si.seriesID=str(dcm.get('SeriesInstanceUID',''))
	si.imageType=list(dcm.get('ImageType',[]))
	si.isSpatial=validPixelArray and dcm.get('ImagePositionPatient',None)!=None
	si.timestep=float(dcm.get('TriggerTime',-1))
	si.isCompressed=not validPixelArray and not getattr(dcm,'_is_uncompressed_transfer_syntax',lambda:False)()
	#si.tags=convertToDict(dcm)

	if 0<=si.timestep<2: # convert from seconds to milliseconds
		si.timestep*=1000

	if validPixelArray:
		#wincenter=dcm.get('WindowCenter',None)
		#winwidth=dcm.get('WindowWidth',None)
		rslope=float(dcm.get('RescaleSlope',1))
		rinter=float(dcm.get('RescaleIntercept',0))
		#rtype=dcm.get('RescaleType',None)
		
		# TODO: proper rescaling?
		if not rescale or rslope==0:
			rslope=1.0
			rinter=0.0
		
		si.allocateImg(si.seriesID+str(si.index),isShared)
		np.asarray(si.img)[:,:]=dcm.pixel_array*rslope+rinter
		si.setMinMaxValues(*minmaxMatrixReal(si.img))
		
	return si


class DicomSeries(object):
	'''Represent a list of Dicom images which are members of a series.'''
	def __init__(self,parent,seriesID,filenames=[]):
		self.parent=parent
		self.seriesID=seriesID
		self.seriesNum=0
		self.desc=''
		self.filenames=list(filenames)
		self.simgs=[] #[None]*len(filenames) # initially empty list of ShareImage objects which will be loaded from Dicoms
		#self.tagmap=OrderedDict()
#		self.lastLoadArgs=() # last arguments used when loading images, pair of (selection,crop) values
		
	def getPropTuples(self):
		return [
			('Series ID',self.seriesID),
			('Series #',str(self.seriesNum)),
			('Description',self.desc),
			('# Images',str(len(self.filenames)))
		]

	def addFile(self,filename):
		if filename not in self.filenames:
			self.filenames.append(filename)
			#self.simgs.append(None)
			
	def addSharedImages(self,images):
		self.simgs+=images
#		for img in images:
#			ind=first(ind for ind,f in enumerate(self.filenames) if img.filename.endswith(f))
#			assert ind!=None,'%r not in %r'%(img.filename,self.filenames)
#			self.simgs[ind]=img
#			self.tagmap

	def getSharedImage(self,filename):
		return first(s for s in self.simgs if s and s.filename.endswith(filename))

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
	'''Represents all the loaded Dicom information for files found in a given root directory.'''
	def __init__(self,rootdir='.'):
		self.series=[]
		self.rootdir=rootdir

	def getSeries(self,seriesID,createNew=False):
		seriesID=str(seriesID)

		s=first(s for s in self.series if s.seriesID==seriesID)
		if s==None and createNew:
			s=DicomSeries(self,seriesID)
			self.series.append(s)

		return s

	def findSeries(self,desc_or_func):
		if isinstance(desc_or_func,str):
			func=lambda s:desc_or_func in s.desc
		else:
			func=desc_or_func

		return first(s for s in self.series if func(s))

	def dump(self,filename):
		'''Dump the data to a pickle file, assumes no image data is present in series objects.'''
		with open(filename,'w') as o:
			pickle.dump(self,o)

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

	def init(self,plugid,win,mgr):
		ImageScenePlugin.init(self,plugid,win,mgr)
		if win:
			win.addMenuItem('Import','DicomLoad'+str(plugid),'&Dicom Directory',self._openDirMenuItem)
			win.addMenuItem('Import','DicomVLoad'+str(plugid),'&Dicom Volume File',self._openVolumeMenuItem)
			win.addMenuItem('Export','DicomExport'+str(plugid),'&Dicom Files',self._exportMenuItem)

	def getDatasets(self):
		return list(self.dirobjs.values())

	def enumSeries(self):
		for dds in self.getDatasets():
			for s in dds.series:
				yield s

	def loadSeriesImages(self,series,selection,loadSequential=False,crop=None):
		f=Future()
		assert selection==None or all(s<len(series.filenames) for s in selection)

		@taskroutine('Loading Image Data')
		def loadSITask(task=None):
			with f:
				if len(series.filenames)>0:
					proccount=chooseProcCount(len(series.filenames),0,10)
					rootdir=series.parent.rootdir

#					loadargs=(tuple(selection) if selection else None,tuple(crop) if crop else None)
#					if loadargs!=series.lastLoadArgs:
#						series.simgs=[]
#
#					series.lastLoadArgs=loadargs
#					series.simgs=[]

					filenames=[series.filenames[i] for i in selection] if selection else series.filenames

					# remove already-loaded images
					filenames=filter(lambda i:series.getSharedImage(i)==None,filenames)

					if len(filenames)>0:
						simgs=loadSharedImages(len(filenames),proccount,task,rootdir,filenames,crop,partitionArgs=(filenames,))

						series.addSharedImages(listSum(simgs.values())) # add new images, there isn't necessarily any order to this list

				f.setObject(series.simgs)

		return self.mgr.runTasks([loadSITask()],f,loadSequential)

	def loadSeries(self,series,name=None,selection=None,loadSequential=False,isTimeDependent=None,crop=None):
		'''Loads the Dicom files for the given series object into a SceneObject subtype.'''

		if isinstance(series,str):
			allseries=listSum(dds.series for dds in self.dirobjs.values())
			series1=first(s for s in allseries if s.seriesID==series)
			assert series1!=None,'Cannot find series %r'%series
			series=series1

		assert len(series.filenames)>0
		assert selection==None or all(s<len(series.filenames) for s in selection)

		f=Future()

		# choose a unique name, based on the given name or the series description
		name=uniqueStr(name or series.desc,[o.getName() for o in self.mgr.enumSceneObjects()]+self.loadedNames)
		self.loadedNames.append(name)

		self.loadSeriesImages(series,selection,loadSequential,crop)

		@taskroutine('Creating Scene Object')
		def createDicomObject(task):
			with f:
				sel=selection or xrange(len(series.filenames))
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

				f.setObject(ImageSceneObject(name,series,imgs,self,isTimeDependent))

		return self.mgr.runTasks([createDicomObject()],f,loadSequential)

	@timing
	def loadDigestFile(self,dirpath,task):
		'''Loads the directory digest pickle file in 'dirpath' if it exists, or creates it if not.'''
		dirpath=os.path.abspath(dirpath)
		dirfiles=list(enumAllFiles(dirpath))
		picklefile=os.path.join(dirpath,'dicomdataset.pickle')

		usePickleFile=False

		# if the pickle file exists and is later than all the files in the directory, set 'usePickleFile' to true
		if os.path.isfile(picklefile):
			picklestat=os.stat(picklefile)
			usePickleFile=all(os.stat(f).st_mtime<=picklestat.st_mtime for f in dirfiles)

		if usePickleFile:
			try:
				result=pickle.load(open(picklefile)) # load the pickle digest file
				for s in result.series: # check that all the files exist, if they don't recreate the dataset
					if not all(map(os.path.exists,s.enumFilePaths())):
						usePickleFile=False
						break
			except:
				usePickleFile=False

		if not usePickleFile:
			result=DicomDataset(dirpath)

			proccount=chooseProcCount(len(dirfiles),0,500)
			ddsmap=createDicomDatasets(len(dirfiles),proccount,task,dirpath,dirfiles,partitionArgs=(dirfiles,))

			for dds in ddsmap.values():
				result.addDataset(dds)
				
			try:
				result.dump(picklefile)
			except:
				pass

		return result

	def loadDirDataset(self,dirpath,loadSequential=False):
		'''Loads the dataset directory as an asset.'''
		f=Future()

		@taskroutine('Loading Dicom Directory')
		def loadDirTask(task):
			with f:
				# load the directory dataset object if it isn't already loaded
				dds=self.loadDigestFile(dirpath,task)
				self.dirobjs[dirpath]=dds

				# add the dataset as an asset to the UI
				self.win.addAsset(dds,dirpath,AssetType._dcm)
				self.win.sync()
				listitem=self.win.findWidgetItem(dds)

				# add each series as a child of the dataset asset item
				for s in dds.series:
					prop=self.win.callFuncUIThread(SeriesPropertyWidget)
					self.win.addAsset(s,str(s),AssetType._dcm,prop,self._updateSeriesPropBox)
					self.win.sync()
					slistitem=self.win.findWidgetItem(s)
					# reset the list item's parent by removing it and adding it to the new paren't child list
					slistitem.parent().removeChild(slistitem)
					listitem.addChild(slistitem)

					# double lambda needed to capture local variables 'prop' and 's'
					caplambda=lambda prop,ss: lambda:self._loadSeriesButton(prop,ss)
					self.win.connect(prop.createButton.clicked,caplambda(prop,s))

				listitem.setExpanded(True) # expand th list of series

				f.setObject(dds)

		if dirpath not in self.dirobjs:
			tasklist=[loadDirTask()]
		else:
			tasklist=[]
			f.setObject(self.dirobjs[dirpath])

		return self.mgr.runTasks(tasklist,f,loadSequential)
		
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
			return self.loadSeries(seriesID)
		
	def loadDicomVolume(self,filename,name=None,interval=1.0,toffset=0.0,position=vec3(),rot=rotator()):
		'''Load a single DICOM file containing a 3D or 4D image volume (ie. ultrasound) using nonstandard tags.'''
		f=Future()
		@taskroutine('Loading Volume File')
		def _loadFile(filename,name,interval,toffset,position,rot,task):
			with f:
				dcm=read_file(filename)
				name=name or splitPathExt(filename)[1]
				
				NT=NonstandardTags
				spacing=vec3(dcm[NT.USpixdimx].value,dcm[NT.USpixdimy].value,dcm[NT.USpixdimz].value)*10	
				dimsize=(dcm[NT.USnumframes].value,dcm[NT.USdepth].value,dcm[NT.USheight].value,dcm[NT.USwidth].value)
				pixeldata=dcm[NT.USpixeldata].value
				
				assert len(pixeldata)==prod(dimsize), 'Pixel data dimension is %i, should be %i'%(len(pixeldata),prod(dimsize))
				
				dat=np.ndarray(dimsize,dtype=np.uint8,buffer=pixeldata,order='C')
				dat=np.transpose(dat,(3,2,1,0))
				
				obj=self.createObjectFromArray(name,dat,interval,toffset,position,rot*rotator(halfpi,0,0),spacing,task=task)
				obj.source=convertToDict(dcm)
				f.setObject(obj)
			
		return self.mgr.runTasks([_loadFile(filename,name,interval,toffset,position,rot)],f)

	def saveImage(self,dirpath,obj,datasetTags={},fileMetaTags={}):
		'''Deprecated, for compatibility only.'''
		return self.saveObject(obj,dirpath,datasetTags=datasetTags,fileMetaTags=fileMetaTags)
		
	def saveObject(self,obj,path,overwrite=False,setFilenames=False,datasetTags={},fileMetaTags={}, *args,**kwargs):
		@taskroutine('Saving DICOM Files')
		def _save(path,obj,datasetTags,fileMetaTags,task=None):
			if not path: # if not path given, choose the one the first source file is in or the current directory
				files=obj.plugin.getObjFiles(obj)
				if files:
					path=os.path.dirname(files[0])
				else:
					path=os.getcwd()

			rootpath=os.path.join(path,getValidFilename(obj.getName()))

			iobj=self.getImageObjectArray(obj)
			matrix=iobj['dat']
			imgmin=matrix.min() # recall the minimal image value, this will become the intercept
			matrix=(matrix-imgmin).astype(np.uint16) # convert to unsigned short, adding imgmin to ensure negative values don't overflow
			
			# TODO: rescale matrix into unsigned 16 bit space properly
			
			timeseqs=obj.getVolumeStacks()
			shape=list(matrix.shape)
			dims=len(shape)
			height,width,slices,timesteps=shape+[1]*(4-dims)

			if dims==4:
				stdat=lambda s,t: matrix[:,:,s,t]
			elif dims==3:
				stdat=lambda s,t: matrix[:,:,s]
			else:
				stdat=lambda s,t: matrix

			if task:
				task.setMaxProgress(slices*timesteps)

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
				# TODO: need to choose instance UIDs this better
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
				'RescaleIntercept' : int(imgmin),
				'PatientName' : 'Anon',
				'SmallestImagePixelValue' : '\\x00\\x00', # these are both default values, the actual image contents may not reflect this
				'LargestImagePixelValue' : '\\xff\\xff',
				'SliceThickness': obj.getVoxelSize().z()
			}

			for s,t in trange(slices,timesteps):
				if task:
					task.setProgress(t+s*timesteps+1)

				pixel_array=stdat(s,t)
				
				index=s+t*slices
				img=obj.images[timeseqs[t][s]]
				filename='%s_%.5i.dcm'%(rootpath,index)

				file_meta = Dataset()

				for k,v in defaultfiletags.items()+fileMetaTags.items():
					setattr(file_meta,k,v)

				ds = FileDataset(filename, {},file_meta = file_meta,preamble="\0"*128)

				for k,v in defaultdatasettags.items()+datasetTags.items():
					setattr(ds,k,v)

				ds.Columns = pixel_array.shape[1]
				ds.Rows = pixel_array.shape[0]
				ds.ImagePositionPatient=list(img.position)
				ds.ImageOrientationPatient=list(img.orientation*vec3(1,0,0))+list(img.orientation*vec3(0,-1,0))
				ds.TriggerTime=int(img.timestep)
				ds.PixelSpacing=list(img.spacing)
				ds.SliceLocation=s*ds.SliceThickness
				ds.SeriesDescription=obj.getName()
				ds.PixelData = pixel_array.tostring()
				
				ds.save_as(filename)
				
		return self.mgr.runTasks(_save(obj,path,datasetTags,fileMetaTags))

	def openChooseSeriesDialog(self,dirpath=None,allowMultiple=True,params=None,subject=None):
		'''
		Opens a dialog for choose which series to load. The starting directory is given by `dirpath', this path is used
		in the dialog, but if left as None an open directory dialog is presented for choosing a directory. If `allowMultiple'
		is true then multiple series can be returned. If `params' is a pair containing a list of ParamDef objects and
		a callable accepting 2 arguments, then a ParamPanel is created in the series choose dialog using the given
		callable as the callback for changed values. The `subject' parameter, if given, should be a string describing
		what is being chosen which is used in the dialog title. The method blocks so long as the dialog is open, and
		returns an iterable of zero or more DicomSeries objects once it is closed.
		'''
		f=Future()
		@self.mgr.callThreadSafe
		def showDialog():
			with f:
				d=ChooseSeriesDialog(self,f,dirpath,self.win,allowMultiple,params,subject)
				d.exec_()

		return f()

	def showTimeMultiSeriesDialog(self,series):
		f=Future()
		def showDialog():
			d=TimeMultiSeriesDialog(toIterable(series),f,self.mgr,self,self.mgr.win)
			d.exec_()

		self.mgr.callThreadSafe(showDialog)
		return f

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
				if indices==range(len(obj.images)):
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

				if isinstance(obj,ImageVolumeRepr):
					args['numplanes']=obj.getNumPlanes()
					script+="%(varname)s.setNumPlanes(%(numplanes)r)\n"
			else:
				script= "%(varname)s=%(pname)s.createRepr(ReprType._%(reprtype)s,imgmat=%(matname)s)\n"

		return setStrIndent(script % args).strip()+'\n'

	def _openDirMenuItem(self):
		series=self.openChooseSeriesDialog()
		objs=[]

		for s in series:
			obj=self.loadSeries(s)
			objs.append(obj)

		if len(objs)>0:
			self.mgr.addFuncTask(lambda:[self.mgr.addSceneObject(o()) for o in objs],'Adding Series Object')
			
	def _openVolumeMenuItem(self):
		filename=self.mgr.win.chooseFileDialog('Choose Dicom filename')
		if filename:
			obj=self.loadDicomVolume(filename)
			self.mgr.addFuncTask(lambda:self.mgr.addSceneObject(obj),'Loading Dicom file')

	def _updateSeriesPropBox(self,series,prop):
		if prop.propTable.rowCount()==0:
			fillTable(series.getPropTuples(),prop.propTable)

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
			selectlist=range(len(series.filenames))[firstind:lastind:stepind]
		else:
			selectlist=None

		obj=self.loadSeries(series,None,selectlist)
		self.mgr.addFuncTask(lambda:self.mgr.addSceneObject(obj()),'Adding Series Object')

	def _exportMenuItem(self):
		obj=self.win.getSelectedObject()
		if not isinstance(obj,(ImageSceneObject,ImageSceneObjectRepr)):
			self.mgr.showMsg('Error: Must select image data object to export','DICOM Export')
		else:
			if isinstance(obj,ImageSceneObjectRepr):
				obj=obj.parent

			outdir=self.mgr.win.chooseDirDialog('Choose directory to save Dicoms to')
			if outdir:
				self.saveObject(outdir,obj,overwrite=True)


addPlugin(DicomPlugin())

