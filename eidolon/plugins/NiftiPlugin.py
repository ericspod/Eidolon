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


from eidolon import vec3, rotator, taskroutine, splitPathExt, halfpi, Future,ImageScenePlugin, ImageSceneObject, ImageSceneObjectRepr
import eidolon

eidolon.addLibraryFile('nibabel-2.3.0.dev0-py3-none-any',False) # http://nipy.org/nibabel/index.html

import nibabel
from nibabel.nifti1 import unit_codes, xform_codes,data_type_codes
import os
import gzip
import math
import unittest
import tempfile
import shutil
import glob
import contextlib
import numpy as np


@contextlib.contextmanager
def processNifti(infile,outfile=None):
    im=nibabel.load(infile)
    dat=im.get_data()
    
    yield im.header,dat
    
    if outfile:
        outim = nibabel.Nifti1Image(dat, im.affine, im.header)
        nibabel.save(outim,outfile)
    
    
def readImageData(infile):
    '''Read Nifti file `infile' and return the image data array.'''
    return nibabel.load(infile).get_data()


def writeImageData(img,outfile):
    '''Write array `img' to Nifti file `outfile' with an identity transform and otherwise default header info.'''
    nibabel.save(nibabel.Nifti1Image(img,np.eye(4)),outfile)
    

class NiftiPlugin(ImageScenePlugin):
    def __init__(self):
        ImageScenePlugin.__init__(self,'Nifti')

    def init(self,plugid,win,mgr):
        ImageScenePlugin.init(self,plugid,win,mgr)
        if win:
            win.addMenuItem('Import','NiftiLoad'+str(plugid),'&Nifti File',self._openFileDialog)
            win.addMenuItem('Export','NiftiExport'+str(plugid),'&Nifti File',self._exportMenuItem)

        # read command line argument, loading files as requested, note these tasks are queued at module load time
        if mgr.conf.hasValue('args','--nifti'):
            niftiload=mgr.conf.get('args','--nifti').split(',')
            filereprs=[]
            for ni in niftiload:
                if ni in eidolon.ReprType and len(filereprs)>0:
                    filereprs[-1][1]=ni
                else:
                    filereprs.append([ni,None])

            @taskroutine('Loading Nifti File(s)')
            def _loadTask(filereprs,task=None):
                for ni,reprtype in filereprs:
                    obj=self.loadObject(ni)
                    self.mgr.addSceneObject(obj)

                    if reprtype!=None:
                        rep=obj.createRepr(reprtype)
                        self.mgr.addSceneObjectRepr(rep)
                        self.mgr.setCameraSeeAll()

            self.mgr.runTasks([_loadTask(filereprs)])

    def getHelp(self):
        return '\nUsage: --nifti=NIfTI-file-path[,representation-type][,...]'

    def acceptFile(self,filename):
        #return splitPathExt(filename,True)[2].lower() in ('.nii','.nii.gz','.hdr')
        return eidolon.hasExtension(filename,'nii','nii.gz','hdr')

    def checkFileOverwrite(self,obj,dirpath,name=None):
        outfile=os.path.join(dirpath,name or obj.getName())+'.nii'
        if os.path.isfile(outfile):
            return [outfile]
        else:
            return []

    def getObjFiles(self,obj):
        if isinstance(obj.source,dict) and obj.source.get('filename',None):
            return [obj.source['filename']]
        else:
            return []

    def renameObjFiles(self,obj,oldname,overwrite=False):
        assert isinstance(obj,eidolon.SceneObject) and obj.plugin==self
        obj.source['filename']=eidolon.renameFile(obj.source['filename'],obj.getName(),overwriteFile=overwrite)

    def copyObjFiles(self,obj,sdir,overwrite=False):
        filename=os.path.join(sdir,os.path.basename(obj.source['filename']))
        eidolon.copyfileSafe(obj.source['filename'],filename,overwrite)
        obj.source['filename']=filename

    def decompressNifti(self,filename,outdir):
        newfilename=os.path.join(outdir,splitPathExt(filename,True)[1]+'.nii')
        with gzip.open(filename) as gf:
            with open(newfilename,'wb') as ff:
                ff.write(gf.read())

        return newfilename

    def loadImage(self,filename,name=None,imgObj=None):
        '''Deprecated, for compatibility only.'''
        return self.loadObject(filename,name,imgObj)

    def loadObject(self,filename,name=None,imgObj=None,**kwargs):
        f=Future()

        @taskroutine('Loading NIfTI File')
        @eidolon.timing
        def _loadNiftiFile(filename,name,imgObj,task):
            with f:
                filename=Future.get(filename)
                name=name or self.mgr.getUniqueObjName(splitPathExt(filename)[1])
                img=imgObj or nibabel.load(filename)

                hdr=dict(img.header)
                hdr['filename']=filename

                pixdim=hdr['pixdim']
                xyzt_units=hdr['xyzt_units']
                x=float(hdr['qoffset_x'])
                y=float(hdr['qoffset_y'])
                z=float(hdr['qoffset_z'])
                b=float(hdr['quatern_b'])
                c=float(hdr['quatern_c'])
                d=float(hdr['quatern_d'])
                toffset=float(hdr['toffset'])
                interval=float(pixdim[4])

                if interval==0.0 and len(img.shape)==4 and img.shape[-1]>1:
                    interval=1.0

                qfac=float(pixdim[0]) or 1.0
                spacing=vec3(pixdim[1],pixdim[2],qfac*pixdim[3])

                if int(hdr['qform_code'])>0:
                    position=vec3(-x,-y,z)
                    rot=rotator(-c,b,math.sqrt(max(0,1.0-(b*b+c*c+d*d))),-d)*rotator(vec3.Z(),halfpi)
                else:
                    affine=img.get_affine()
                    position=vec3(-affine[0,3],-affine[1,3],affine[2,3])
                    rmat=np.asarray([affine[0,:3]/-spacing.x(),affine[1,:3]/-spacing.y(),affine[2,:3]/spacing.z()])
                    rot=rotator(*rmat.flatten().tolist())*rotator(vec3.Z(),halfpi)

                xyzunit=xyzt_units & 0x07 # isolate space units with a bitmask of 7
                tunit=xyzt_units & 0x38 # isolate time units with a bitmask of 56

                if tunit==0: # if no tunit provided, try to guess
                    if interval<1.0:
                        tunit=unit_codes['sec']
                    elif interval>1000.0:
                        tunit=unit_codes['usec']

                # convert to millimeters
                if xyzunit==unit_codes['meter']:
                    position*=1000.0
                    spacing*=1000.0
                elif xyzunit==unit_codes['micron']:
                    position/=1000.0
                    spacing/=1000.0

                # convert to milliseconds
                if tunit==unit_codes['sec']:
                    toffset*=1000.0
                    interval*=1000.0
                elif tunit==unit_codes['usec']:
                    toffset/=1000.0
                    interval/=1000.0

                dobj=img.dataobj
                datshape=tuple(d or 1 for d in dobj.shape) # dimensions are sometimes given as 0 for some reason?
                
                # reading file data directly is expected to be faster than using nibabel, specifically by using memmap
                if filename.endswith('.gz'):
                    dat=img.get_data()
                    #dat=np.asanyarray(dobj) # same as the above
                    
#                    with gzip.open(filename) as o: # TODO: not sure if this is any faster than the above
#                        o.seek(dobj.offset) # seek beyond the header
#                        dat=np.frombuffer(o.read(),dobj.dtype).reshape(datshape,order=dobj.order)
                else:
                    # mmap the image data below the header in the file
                    dat=np.memmap(dobj.file_like,dobj.dtype,'r',dobj.offset,datshape,dobj.order)

                dat=eidolon.transposeRowsColsNP(dat) # transpose from row-column to column-row

                obj=self.createObjectFromArray(name,dat,interval,toffset,position,rot,spacing,task=task)
                obj.source=hdr

                # apply slope since this isn't done automatically when using memmap/gzip
                if not filename.endswith('.gz'):
                    eidolon.applySlopeIntercept(obj,*img.header.get_slope_inter())

                f.setObject(obj)

        @taskroutine('Loading Analyze File')
        def _loadAnalyzeFile(filename,name,imgObj,task):
            with f:
                filename=Future.get(filename)
                name=name or self.mgr.getUniqueObjName(splitPathExt(filename)[1])
                img=imgObj or nibabel.load(filename)

                dat=dat=np.asanyarray(img.dataobj)
                hdr=dict(img.get_header())
                hdr['filename']=filename

                pixdim=hdr['pixdim']
                interval=float(pixdim[4])

                if interval==0.0 and len(img.shape)==4 and img.shape[-1]>1:
                    interval=1.0

                spacing=vec3(pixdim[1],pixdim[2],pixdim[3])
                dat=eidolon.transposeRowsColsNP(dat) # transpose from row-column to column-row

                obj=self.createObjectFromArray(name,dat,interval,0,vec3(),rotator(),spacing,task=task)
                obj.source=hdr
                f.setObject(obj)

        func=_loadAnalyzeFile if filename.endswith('.hdr') else _loadNiftiFile

        return self.mgr.runTasks([func(filename,name,imgObj)],f)

    def saveImage(self,filename,obj,setObjArgs=False,**kwargs):
        '''Deprecated, for compatibility only.'''
        return self.saveObject(obj,filename,kwargs.get('overwrite',False),setObjArgs,**kwargs)

    def saveObject(self,obj,path,overwrite=False,setFilenames=False,**kwargs):
        f=Future()

        @taskroutine('Saving Nifti File')
        def _saveFile(path,obj,kwargs,task):
            with f:
                assert isinstance(obj,ImageSceneObject)

                if os.path.isdir(path):
                    path=os.path.join(path,obj.getName())

                if not overwrite and os.path.exists(path):
                    raise IOError('File already exists: %r'%path)

                if not eidolon.hasExtension(path,'nii','nii.gz'):
                    path+='.nii'

                if 'datatype' in kwargs:
                    datatype=kwargs.pop('datatype')
                elif isinstance(obj.source,dict) and 'datatype' in obj.source:
                    datatype=data_type_codes.dtype[int(obj.source['datatype'])]
                else:
                    datatype=np.float32

                mat=self.getImageObjectArray(obj,datatype)
                dat=mat['array']
                pos=mat['pos']
                spacex,spacey,spacez=mat['spacing']
                rot=rotator(vec3(0,0,1),math.pi)*mat['rot']*rotator(vec3(0,0,1),-halfpi)
                toffset=mat['toffset']
                interval=mat['interval']

                affine=np.array(rot.toMatrix())
                affine[:,3]=-pos.x(),-pos.y(),pos.z(),1.0

                dat=eidolon.transposeRowsColsNP(dat) # transpose from row-column to column-row

                imgobj=nibabel.nifti1.Nifti1Image(dat,affine)

                # header info: http://nifti.nimh.nih.gov/pub/dist/src/niftilib/nifti1.h
                hdr={
                    'pixdim':np.array([1.0,spacex,spacey,spacez if spacez!=0.0 else 1.0,interval,1.0,1.0,1.0],np.float32),
                    'toffset':toffset,
                    'slice_duration':interval,
                    'xyzt_units':unit_codes['mm'] | unit_codes['msec'],
                    'qform_code':xform_codes['aligned'],
                    'sform_code':xform_codes['scanner'],
                    'datatype':data_type_codes.code[datatype]
                }

                hdr.update(kwargs)

                for k,v in hdr.items():
                    if k in imgobj.header:
                        imgobj.header[k]=v

                nibabel.save(imgobj,path)

                if setFilenames:
                    obj.plugin.removeObject(obj)
                    obj.plugin=self
                    obj.source=dict(nibabel.load(path).get_header())
                    obj.source['filename']=path
                elif isinstance(obj.source,dict) and 'filename' in obj.source:
                    obj.source['filename']=path

                f.setObject(imgobj)

        return self.mgr.runTasks([_saveFile(path,obj,kwargs)],f)

    def _openFileDialog(self):
        filename=self.mgr.win.chooseFileDialog('Choose NIfTI/Analyze filename',filterstr='NIfTI/Analyze Files (*.nii *.nii.gz *.hdr)')
        if filename!='':
            self.mgr.addFuncTask(lambda:self.mgr.addSceneObject(self.loadObject(filename)),'Importing NIfTI file')

    def _exportMenuItem(self):
        obj=self.win.getSelectedObject()
        if not isinstance(obj,(ImageSceneObject,ImageSceneObjectRepr)):
            self.mgr.showMsg('Error: Must select image data object to export','NIfTI Export')
        else:
            if isinstance(obj,ImageSceneObjectRepr):
                obj=obj.parent

            filename=self.mgr.win.chooseFileDialog('Choose NIfTI filename',filterstr='NIfTI Files (*.nii *.nii.gz)',isOpen=False)
            if filename!='':
                f=self.saveObject(obj,filename,True)
                self.mgr.checkFutureResult(f)

    def getScriptCode(self,obj,**kwargs):
        configSection=kwargs.get('configSection',False)
        namemap=kwargs.get('namemap',{})
        convertpath=kwargs['convertPath']
        varname=namemap[obj]
        script=''
        args={}

        if not configSection and isinstance(obj,ImageSceneObject):
            filename=convertpath(obj.source['filename'])

            args={
                'varname':varname,
                'objname':obj.name,
                'filename':filename
            }

            script+='%(varname)s = Nifti.loadObject(%(filename)s,%(objname)r)\n'

        elif isinstance(obj,ImageSceneObjectRepr):
            args={
                'varname':varname,
                'pname':namemap[obj.parent],
                'reprtype':obj.reprtype,
                'matname':namemap.get(obj.getMaterialName(),'Greyscale')
            }

            if configSection:
                script= ImageScenePlugin.getScriptCode(self,obj,setMaterial=False,**kwargs)
            else:
                script= "%(varname)s=%(pname)s.createRepr(ReprType._%(reprtype)s,imgmat=%(matname)s)\n"

        return eidolon.setStrIndent(script % args).strip()+'\n'

### Add plugin to environment

eidolon.addPlugin(NiftiPlugin())

### Unit tests

class TestNiftiPlugin(unittest.TestCase):
    def setUp(self):
        self.tempdir=tempfile.mkdtemp()
        self.plugin=eidolon.getSceneMgr().getPlugin('Nifti')
        
        self.vfunc=lambda x,y,z,t:(x+1)*1000+(y+1)*100+(z+1)*10+t+1
        self.volarr=np.fromfunction(self.vfunc,(21,33,46,17))
        self.vpos=vec3(-10,20,-15)
        self.vrot=rotator(0.1,-0.2,0.13)

        self.vol=self.plugin.createObjectFromArray('TestVolume',self.volarr,pos=self.vpos,rot=self.vrot)
        
    def tearDown(self):
        shutil.rmtree(self.tempdir)
        
    def rotatorsEqual(self,r1,r2):
        r1=np.asarray(list(r1))
        r2=np.asarray(list(r2))
        
        return np.sum(np.abs(r1-r2))
        
    def testSaveLoadVolume(self):
        '''Test saving and loading a volume image.'''
        self.plugin.saveObject(self.vol,self.tempdir)
        filename=eidolon.first(glob.glob(self.tempdir+'/*.nii'))
        
        self.assertIsNotNone(filename)
        
        obj1=self.plugin.loadObject(filename)
        trans=obj1.getVolumeTransform()
        
        self.assertEqual(self.vpos,trans.getTranslation())
        self.assertTrue(self.rotatorsEqual(self.vrot,trans.getRotation()))
        
        self.assertEqual(self.vol.getArrayDims(),obj1.getArrayDims())
        
        with eidolon.processImageNp(obj1) as arr1:
            self.assertEqual(self.volarr.shape,arr1.shape)
            
            diff=np.sum(np.abs(self.volarr-arr1))
            self.assertAlmostEqual(diff,0,4,'%r is too large'%(diff,))
            