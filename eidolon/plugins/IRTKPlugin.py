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


import os
import sys
import time
import glob
import math
import subprocess
import socket
import pickle
import traceback
import shutil
import itertools
import threading

try:
    import SocketServer as socketserver
except:
    import socketserver

from contextlib import closing
import numpy as np
from numpy.fft import fftn,ifftn,fftshift,ifftshift
from scipy.ndimage import zoom,grey_dilation

import eidolon
from eidolon import (
    QtWidgets, copyfileSafe, cropCenter, deformImage2D,
    enum, printFlush, taskroutine, taskmethod, execBatchProgram, concurrent, addPathVariable,isLinux, isWindows,
    getLibraryDir, timing, first, vec3, Future, extendImage, readBasicConfig, MeshSceneObject, ImageSceneObject
)

from .SegmentPlugin import DatafileParams,SegSceneObject,SegmentTypes
from ..ui import Ui_mtServerForm


InterpTypes=enum(
    ('Linear','-linear'),
    ('Bezier Spline','-bspline'),
    ('Cubic Spline','-cspline'),
    ('Truncated Sinc','-sinc'),
    ('Shape Based','-sbased'),
    ('Gaussian','-gaussian sigma')
)


ServerMsgs=enum(
    ('OK',(),'OK Server Response; no values'),
    ('Except',(Exception,str),'Exception from Server; exception value, stack trace string info'),
    ('Stat',(int,),'Status Request for Job; Job ID value'),
    ('RStat',(int,int,int,str),'Status Response; process exit code (None if still running), # of files so far, total # of files, job dir'),
    ('StartMotionTrack',(bool,str,str,str,str,str,float,dict,str),'Sending motion track job to server;true if data is file path, file blob otherwise, track file,mask file, param filename, directory name, adaptive, config values dict, root directory'),
    ('RStart',(int,),'Job Send Response; Job ID value'),
    ('GetResult',(int,bool),'Get job results; job ID value, true if absolute file paths are requested'),
    ('RGetResult',(list,),'Returned job results; list of file paths or file data blobs'),
    ('Check',(),'Request the username of whoever started the server; empty'),
    ('RCheck',(str,),'Username response; username string'),
    ('Kill',(int,),'Job kill command; Job ID value'),
    ('RKill',(bool,),'Job kill response; True if successful, False if job was not running'),
    valtype=(tuple,str),
    doc='Server request and response messages, containing the types of the arguments and a description'
)

TrackTypes=enum('motiontrackmultimage','gpunreg','mirtkregister','mirtkregister1file')

JobMetaValues=enum(
    'pid','rootdir','numtrackfiles','timesteps','tracktype','trackobj','maskobj','trackfile','maskfile',
    'paramfile','adaptive','resultcode','startdate','enddate','transform','pixdim',
    doc='Names of fields in job/track ini files storing metadata about the associated operation/job'
)


EnvironVars=enum('LD_LIBRARY_PATH','DYLD_LIBRARY_PATH')

trackconfname='track.ini'


def isTrackDir(path):
    '''
    Returns True if `path' is the path to a directory containing tracking information. This is done asynchronously with
    a daemon thread. The function will block for up to 1 second and return False if an answer isn't calculated by then.
    This ensures the UI is not held up by a slow file system.
    '''
    @eidolon.asyncfunc
    def _check():
        if not os.path.isdir(path):
            return False

        if not os.path.isfile(os.path.join(path,trackconfname)):
            return False

        return len(glob.glob(path+'/*.dof*'))>0

    t=_check()

    return t.result(1.0) or False


def isPositiveDefinite(mat):
    '''Returns True if `mat' is a positive definite matrix (ie. all positive eigenvalues).'''
    return np.all(np.linalg.eigvals(mat) >= 0)


def detagImage(obj,coresize,revert=False):
    with eidolon.processImageNp(obj,True) as im:
        xmax,ymax,zmax,tmax=im.shape
        xs = int(math.floor(xmax/2))
        ys = int(math.floor(ymax/2))
        zs = int(math.floor(zmax/2))
        x,y,z =np.meshgrid(range(-ys,ys+ymax%2),range(-xs,xs+xmax%2),range(-zs,zs+zmax%2))

        dist=np.sqrt(x**2+y**2+z**2)
        c=(dist < math.sqrt(3*(coresize**2)))
        if revert:
            c=(c==0)

        for t in range(tmax):
            mat1 = fftshift(fftn(im[...,t]))
            mat2=mat1*c
            im[...,t]=ifftn(ifftshift(mat2))


@concurrent
def applyMotionTrackRange(process,exefile,cwd,isInvert,filelists,extraArgs,environ):
    oldenviron={ev:os.environ[ev] for ev in environ if ev in os.environ}

    for ev,val in environ.items():
        os.environ[ev]=val

    results=[]
    for i,(infile,outfile,doffile,ttime) in enumerate(filelists):
        args=[infile,outfile,'-dofin',doffile]

        if isInvert: # invert the transformation
            args.append('-invert')

        if ttime>=0: # timestep selection
            args+=['-St',str(ttime)]

        args+=extraArgs

        ret,out=execBatchProgram(exefile,*args,cwd=cwd)
        results.append((ret,out,args))
        process.setProgress(i+1)

    for ev,val in oldenviron.items():
        os.environ[ev]=val

    return results


@taskroutine('Applying Transformation')
def applyMotionTrackTask(exefile,cwd,isInvert,filelists,extraArgs=[],numProcs=0,task=None):
    environ={ev:os.environ[ev] for ev in map(first,EnvironVars) if ev in os.environ}
    
    results=applyMotionTrackRange(len(filelists),numProcs,task,exefile,cwd,isInvert,
                                  filelists,extraArgs,environ,partitionArgs=(filelists,))
    
    for ret,out,args in eidolon.sumResultMap(results):
        if ret!=0:
            raise IOError('Command failed with return code %r: %r\n%s'%(ret,' '.join([exefile]+list(args)),out))


class IRTKPluginMixin(object):
    def init(self,plugid,win,mgr):
        self.Nifti=mgr.getPlugin('Nifti')
        self.Dicom=mgr.getPlugin('Dicom')
        self.Meta=mgr.getPlugin('MetaImg')
        self.Slice=mgr.getPlugin('SlicePlugin')
        self.VTK=mgr.getPlugin('VTK')
        self.CHeart=mgr.getPlugin('CHeart')
        self.Plot=mgr.getPlugin('Plot')
        self.Segment=mgr.getPlugin('Segment')

        self.serverdir=self.mgr.getUserAppDir()
        self.irtkdir=os.path.join(getLibraryDir(),'IRTK')

        self.fixshort=os.path.join(self.irtkdir,'fixshort.txt')
        self.patient1e4=os.path.join(self.irtkdir,'patient_lambda1-1e-4.txt')
        self.patient1e6=os.path.join(self.irtkdir,'patient_lambda1-1e-6.txt')
        self.nreg_default=os.path.join(self.irtkdir,'nreg_default.txt')
        self.gpu_nreg_default=os.path.join(self.irtkdir,'gpu_nreg_cc_L3_CP40x40x40_l10.cfg')

        self.exesuffix=''
        if isWindows:
            self.exesuffix='.exe'
        elif isLinux:
            self.exesuffix='.bin'

        # by default setup the IRTK executable paths to be those that come with the visualizer
        localirtkpath=lambda i:os.path.join(self.irtkdir,i)+self.exesuffix
        self.irtkpath=localirtkpath

        # if the system-installed IRTK is present, use it instead
        if isLinux and mgr.conf.get(eidolon.platformID,'usesystemirtk').lower()!='false' and os.path.exists('/usr/bin/irtk-rreg'):
            self.irtkpath=lambda i:('/usr/bin/irtk-'+i) if os.path.exists('/usr/bin/irtk-'+i) else localirtkpath(i)
        else:
            addPathVariable(EnvironVars.LD_LIBRARY_PATH,self.irtkdir)

        self.spatialcorrect=self.irtkpath('spatial_correct')
        self.rreg=self.irtkpath('rreg')
        self.motiontrack=self.irtkpath('motiontrackmultimage')
        self.gpu_nreg=self.irtkpath('gpu_nreg') # not part of IRTK

        # setup MIRTK variables
        if isWindows:
            self.mirtkdir=os.path.join(getLibraryDir(),'MIRTK','Win64')
        elif isLinux:
            self.mirtkdir=os.path.join(getLibraryDir(),'MIRTK','Linux')
            self.exesuffix=''
            addPathVariable(EnvironVars.LD_LIBRARY_PATH,self.mirtkdir)
        else:
            self.mirtkdir=os.path.join(getLibraryDir(),'MIRTK','OSX')
            addPathVariable(EnvironVars.DYLD_LIBRARY_PATH,self.mirtkdir)

        self.ffd_motion=os.path.join(getLibraryDir(),'MIRTK','ffd_motion.cfg')

        self.register=os.path.join(self.mirtkdir,'register')+self.exesuffix
        self.info=os.path.join(self.mirtkdir,'info')+self.exesuffix
        self.transimage=os.path.join(self.mirtkdir,'transform-image')+self.exesuffix
        self.transpts=os.path.join(self.mirtkdir,'transform-points')+self.exesuffix
        self.editimage=os.path.join(self.mirtkdir,'edit-image')+self.exesuffix
        self.decimatesurf=os.path.join(self.mirtkdir,'decimate-surface')+self.exesuffix
        self.convertdof=os.path.join(self.mirtkdir,'convert-dof')+self.exesuffix
        self.composedofs=os.path.join(self.mirtkdir,'compose-dofs')+self.exesuffix

    def getCWD(self):
        '''This method must be overridden to return the current working directory (ie. project directory).'''
        pass

    def getNiftiFile(self,name):
        '''Get the NIfTI file in the current context starting with `name', '.nii' is appended to the filename.'''
        return self.getLocalFile(eidolon.ensureExt(name,'.nii'))

    def getLogFile(self,name):
        '''Get the log file in the current context starting with `name', '.log' is appended to the filename if not already present.'''
        return self.getLocalFile(eidolon.ensureExt(name,'.log'))

    def getLocalFile(self,name):
        '''Get a file with name `name' in the current context (ie. project directory).'''
        pass

    def getUniqueObjName(self,name):
        '''Get a unique object name which won't cause files to be overwritten.'''
        pass

    def getTrackingDirs(self,root=None):
        '''Returns a list of absolute path directory names in the current context or in `root' containing tracking information.'''
        root=root or self.getLocalFile('.')
        return sorted(filter(isTrackDir,glob.glob(root+'/*')))

    def addObject(self,obj):
        '''
        Add an object to the current context (ie. project). If the object is already present, this method should still
        succeed but still do the internal bookkeeping operations needed (ie. save the project).
        '''
        pass

    @taskmethod('Load Nifti Files')
    def loadNiftiFiles(self,filenames,task):
        '''
        Loads the given NIfTI file paths. The argument `filenames' can be a list of paths, or a Future returning such
        a list. The result value is a Future which eventually will hold the loaded ImageSceneObject instances. Each
        loaded file is added to the current context by being passed to addObject().
        '''
        filenames=Future.get(filenames)
        objs=[]
        for filename in filenames:
            filename=os.path.abspath(filename)
            if not filename.startswith(self.getCWD()):
                if filename.endswith('.nii.gz'): # unzip file
                    newfilename=self.Nifti.decompressNifti(filename,self.getCWD())
                else:
                    newfilename=self.getUniqueLocalFile(filename)
                    eidolon.copyfileSafe(filename,newfilename,True)
                filename=newfilename

            nobj=self.Nifti.loadObject(filename)
            self.addObject(nobj)
            objs.append(nobj)

        return objs

    def getUniqueShortName(self,*comps,**kwargs):
        '''Create a name guaranteed to be unique in the current context using the given arguments with createShortName().'''
        return self.getUniqueObjName(eidolon.createShortName(*comps,**kwargs))

    def getUniqueLocalFile(self,name):
        '''Get a version of the filename `name' which is guarranteed to be unique in the current context.'''
        _,name,ext=eidolon.splitPathExt(name)
        return self.getLocalFile(self.getUniqueObjName(name)+ext)

    def getServerAddrPort(self):
        '''Returns the server address and port, default is ('localhost',15000).'''
        return 'localhost',15000

    def setServerAddrPort(self,addr,port):
        '''Set the server address and port, setting a value as None will keep existing value.'''
        pass

    def _removeNamedObjs(self,*names):
        objs=[o for o in self.mgr.enumSceneObjects() if o.getName() in names]
        for o in objs:
            self.mgr.removeSceneObject(o)

    def saveToNifti(self,objs,setObjArgs=False):
        f=Future()
        @taskroutine('Converting Image Object(s) to NIfTI')
        def _convertTask(objs,setObjArgs,task=None):
            with f:
                filenames=[]

                for obj in objs:
                    obj=Future.get(obj)
                    if obj:
                        filename=self.getNiftiFile(self.getUniqueObjName(obj.getName()))
                        printFlush('Saving',filename)
                        self.Nifti.saveImage(filename,obj,setObjArgs)
                        filenames.append(filename)

                f.setObject(filenames)

        return self.mgr.runTasks(_convertTask(objs,setObjArgs),f)

    def _checkProgramTask(self,result):
        @taskroutine('Checking Program Results')
        def _check(result,task=None):
            result=Future.get(result)

            if result==None:
                raise Exception('None result from program')
            elif isinstance(result,Exception):
                raise result
            elif result[0]!=0:
                self.mgr.showMsg('The program operation failed (Exit code: %i)'%result[0],'Operation Failed',result[1])
                if task:
                    task.flushQueue=True

        self.mgr.runTasks(_check(result))

    def correctNiftiParams(self,sourceobj,destfile,makeProspective=False):
        '''
        Corrects the parameters in the NIfTI file `destfile' with those in the ImageSceneObject or filename `sourceobj'.
        IRTK munges timestep values amongst other things so use this to reset them to what they were in the original.
        If `makeProspective' is True then half of the average difference between timesteps is added to each time.
        '''
        @taskroutine('Correcting NIfTI Header')
        def _correct(sourceobj,destfile,makeProspective,task):
            if isinstance(sourceobj,str):
                sourceobj=self.findObject(sourceobj,False) or self.Nifti.loadImage(sourceobj)

            destobj=self.Nifti.loadImage(destfile)

            timesteps=sourceobj.getTimestepList()
            if makeProspective:
                value=eidolon.avgspan(timesteps)/2
                timesteps=[ts+value for ts in timesteps]

            destobj.setTimestepList(timesteps)

            self.Nifti.saveObject(destobj,destfile,True)

        self.mgr.runTasks(_correct(sourceobj,destfile,makeProspective))

    def applyImageDof(self,inname,outname,doffile,cwd,correctNifti=True):
        logfile=self.getLogFile('editimage.log')
        app=self.editimage # self.headertool
        f=self.mgr.execBatchProgramTask(app,inname,outname,'-dofin',doffile,logfile=logfile,cwd=cwd)
        self._checkProgramTask(f)

        if correctNifti:
            self.correctNiftiParams(inname,outname)

        return f

    def load3DTagSeries(self,tagobj,makeProspective,loadPlanes=False,makeDetag=True,spacing=vec3(1),tryFix=True):
        '''
        Load the 3D TAG image series and process it into a time-dependent volume combining the 3 magnitude orientations.
        This assumes `tagobj' contains images for 3 orientations in an overlapping volume, with phase and magnitude
        volumes for each orientation and timestep. This ignores the phase images which are assumed to have negative
        minimum image values, while the magnitude images should have 0 as the minimum value.
        '''
        f=Future()
        @taskroutine('Generating Tagged and Detagged Image Series')
        def _loadtags(tagobj,makeProspective,loadPlanes,makeDetag,spacing,tryFix,task):
            with f:
                tagged=self.getUniqueObjName('tagged3d')
                detagged=self.getUniqueObjName('detag3d')
                coresize=4
                objs=[]
                loadnames=[]

                tagobj=Future.get(tagobj)

                magimgs=tagobj.images
                img1=magimgs[0]
                # magnitude images only, remove phase images assuming these are the last half of the series
                if any(i.isSameLocation(img1) and i.timestep==img1.timestep for i in magimgs[1:]):
                    magimgs=tagobj.images[:len(tagobj.images)/2]

                tagobj=ImageSceneObject('tempobj',tagobj.source,magimgs,tagobj.plugin)
                tsinds=tagobj.getTimestepIndices()
                tso=tagobj.getOrientMap()
                ts=[t[0] for t in tsinds]

                if len(tso)!=3:
                    raise IOError('Should have 3 orientations: %r'%list(tso.keys()))

                #isorthos=[o1.isOrthogonalTo(o2) or o1.isOrthogonalTo(o3) for o1,o2,o3 in successive(tso,3,True)]

                if makeProspective: # prospective timing, add half the average difference between timesteps to each timestep
                    value=eidolon.avgspan(ts)/2
                    ts=[t+value for t in ts]

                # For each of the 3 orientations, take the magnitude images for that orientation and create a temporary
                # image object. Each object will then have all the images over time for one of the tag orientations.
                for o,olist in enumerate(tso.values()):
                    oimages=eidolon.indexList(olist,magimgs)
                    plane=ImageSceneObject('%s_plane%i'%(tagged,o),tagobj.source,oimages,self,True)
                    plane.setTimestepList(ts)
                    plane.calculateAABB(True)
                    objs.append(plane)

#                   # TODO: Sort out the definite positive issue to remove or otherwise handle bad tag volumes
#                   # NOTE: Sometimes a positive definite image is in the correct position, this isn't a reliable mechanism for
#                   #       identifying bad tag series anymore
#                   mat=np.matrix(plane.images[0].orientation.toMatrix())
#                   # flip volume if its matrix is bogus
#                   if tryFix and isPositiveDefinite(mat):
#                       for i in plane.images:
#                           sx,sy=i.spacing
#                           i.spacing=(sx,-sy)
#                           i.calculateDimensions()
#
#                       plane.calculateAABB(True)

                if tryFix:
                    bbs=[o.aabb for o in objs]
                    #avgcenter=avg((b.center for b in bbs),vec3())
                    dist,mid=min((b1.center.distTo(b2.center),(b1.center+b2.center)*0.5) for b1,b2 in itertools.product(bbs,repeat=2) if b1 is not b2)

                    for bb,o in zip(bbs,objs):
                        #if bb.center.distTo(avgcenter)>bb.radius/3:
                        if bb.center.distTo(mid)>dist*3:
                            for i in o.images:
                                sx,sy=i.spacing
                                i.spacing=(sx,-sy)
                                i.calculateDimensions()

                            o.calculateAABB(True)
                            break

                # create an image within the plane-aligned series, disregarding those volumes that may be in an incorrect orientation
                tag=tagobj.plugin.createIntersectObject(tagged,objs,len(ts),spacing)
                tag.setTimestepList(ts)

                mergefunc='(prod(v/100.0 for v in vals)**(1.0/len(vals)))*100.0'
                eidolon.mergeImages(objs,tag,mergefunc,task) # merge the plane-aligned series using the function

                saveobjs=[tag]
                loadnames=[self.getNiftiFile(tagged)]

                # create a detagged version of the tag image
                if makeDetag:
                    detag=tag.plugin.clone(tag,detagged)
                    detagImage(detag,coresize) # turn the tag image into a detagged image
                    saveobjs.append(detag)
                    loadnames.append(self.getNiftiFile(detagged))

                # load the objects for each plane-aligned image
                if loadPlanes:
                    saveobjs+=objs
                    loadnames+=[self.getNiftiFile(o.getName()) for o in objs]

                self.saveToNifti(saveobjs)
                for o in saveobjs:
                    o.clear()

                f.setObject(self.loadNiftiFiles(loadnames))

        return self.mgr.runTasks(_loadtags(tagobj,makeProspective,loadPlanes,makeDetag,spacing,tryFix),f)

    def createSegObject(self,srcname,segtype):
        f=Future()
        @taskroutine('Generating Segmentation Object')
        def _genseg(srcname,segtype,task):
            with f:
                name=self.getUniqueShortName(srcname,'Seg')
                seg=self.Segment.createSegmentObject(self.getLocalFile(name),name,segtype)
                seg.set(DatafileParams.srcimage,srcname)
                seg.save()
                self.addObject(seg)
                f.setObject(seg)

        return self.mgr.runTasks(_genseg(srcname,segtype),f)

    def createTimeRegStack(self,template,stack,trname=None,loadObject=True):
        '''
        Create a new image series by temporally registering `stack' to `template'. This involves selecting timesteps
        in `stack' which are closest to the timesteps in `template', then copying the images for these timesteps into
        the resulting object. Eg. if `template' has timesteps [0,7] and `stack' has [0,4,6,10], the resulting object
        will have 2 timesteps [0,7] whose images are copied from timesteps 0 and 6 in `stack'. This assumes that
        `template' has fewer timesteps that `stack'.
        '''
        f=Future()
        @taskroutine('Time-registering Images')
        def _timereg(template,stack,trname,loadObject,task):
            with f:
                assert template
                assert stack

                if not trname: # if no name given, choose one based off `stack'
                    trname=eidolon.createShortName('TimeReg',stack.getName(),'to',template.getName())
                    if not loadObject: # if we're not reloading the object, ensure the name is unique
                        trname=self.getUniqueShortName(trname)

                tempts=template.getTimestepList()
                stackts=stack.getTimestepList()

                assert len(tempts)<=len(stackts),'Template has more timesteps than stack, %r>%r' %(len(tempts),len(stackts))

                obj=stack.plugin.extractTimesteps(stack,trname,None,tempts,True)

                assert obj.getTimestepList()==tempts,'%r != %r'%(obj.getTimestepList(),tempts)

                if loadObject:
                    filenames=self.saveToNifti([obj])
                    self._removeNamedObjs(trname)
                    obj=self.loadNiftiFiles(filenames)[0]

                f.setObject(obj)

        return self.mgr.runTasks([_timereg(template,stack,trname,loadObject)],f,False)

    def spatialCorrect(self,target,before,after,prefix,extras=[],xyOnly=True,trans=True,logfile=None,cwd=None):
        '''
        Determine the correction for `target'.nii necessary to align the images spatially, then apply this correction
        to `before'.nii to produce `after'.nii, also apply the correction to every i in `extras' which produces and
        `prefix'`i'.nii for each.
        '''
        logfile=logfile or self.getLogFile('spatialcorrect.log')
        cwd=cwd or self.getCWD()

        args=[target+'.nii',before+'.nii',after+'.nii']
        if xyOnly:
            args.append('-xy_only')
        if trans:
            args.append('-translation')
        if extras:
            args+=['-extraimage',str(len(extras)),prefix]+[e+'.nii' for e in extras]

        f1=self.mgr.execBatchProgramTask(self.spatialcorrect,*args,logfile=logfile,cwd=cwd)
        self._checkProgramTask(f1)
        return f1

    def alignShortStack(self,saxname,segname,templatename=None):
        assert os.path.isfile(self.getNiftiFile(saxname)), 'Cannot find %r'%saxname
        origsegname=segname

        # if the given segment is a segmentation object, generate the mask image
        segobj=self.findObject(segname)
        if isinstance(segobj,SegSceneObject):
            saxobj=self.findObject(saxname)
            segname='asaxtemp_SegMask'
            obj=self.Segment.createImageMask(segobj,segname,saxobj,'2 if len(contours)>1 else 3')
            self.saveToNifti([obj])

        # choose names for log files and intermediate/final object names
        cwd=self.getCWD()
        logfile1=self.getLogFile('spatialcorrect1.log')
        logfile2=self.getLogFile('spatialcorrect2.log')
        doffile='shortto3d.dof'

        timeregname='asaxtemp_TimeReg'
        corregname='asaxtemp1_'+timeregname
        corregname2='asaxtemp2_'+timeregname
        tempsaxname='asaxtemp1_'+saxname
        tempsaxname2='asaxtemp2_'+tempsaxname
        tempsegname='asaxtemp1_'+segname
        tempsegname2='asaxtemp2_'+tempsegname
        finalname=self.getUniqueShortName('Aligned',os.path.splitext(saxname)[0])
        finalseg=self.getUniqueShortName('AlignMask',os.path.splitext(origsegname)[0])
        finalsaxnii=self.getNiftiFile(finalname)
        finalsegnii=self.getNiftiFile(finalseg)

        # extract the first timestep of the sax as the frame time-registered to the segmentation
        saxobj=self.findObject(saxname)
        timeregobj=saxobj.plugin.extractTimesteps(saxobj,timeregname,indices=[0])
        self.saveToNifti([timeregobj])

        # correct the time-registered stack using the segmentation and apply to the time-reg, original short axis and segmentation
        f1=self.spatialCorrect(segname,timeregname,corregname,'asaxtemp1_',[saxname,segname],logfile=logfile1,cwd=cwd)
        # correct the time-registered stack again using itself and apply to the time-reg, original short axis and segmentation
        f2=self.spatialCorrect(corregname,corregname,corregname2,'asaxtemp2_',[tempsaxname,tempsegname],logfile=logfile2,cwd=cwd)

        if templatename: # if the template is given, rigidly register the results to it
            # determine the registration of the corrected time-reg to the template image (morpho) and apply to the fixed short-axis
            f3,f4=self.rigidRegisterStack(templatename,corregname2,tempsaxname2,finalname,doffile,self.fixshort,False)
            # apply the dof file from the above to the fixed segmentation
            self.applyImageDof(self.getNiftiFile(tempsegname2),finalsegnii,doffile,cwd,False)
        else:
            # move the final results to their new names
            self.mgr.addFuncTask(lambda:shutil.move(self.getNiftiFile(tempsaxname2),finalsaxnii))
            self.mgr.addFuncTask(lambda:shutil.move(self.getNiftiFile(tempsegname2),finalsegnii))
            f3,f4=None,None

        # fix the header values in the final nifti, necessary since IRTK doesn't preserve time info in output niftis
        self.correctNiftiParams(saxname,finalsaxnii)
        # load the nifti files
        self.loadNiftiFiles([finalsaxnii,finalsegnii])
        # delete the temporary files
        self.removeFilesTask(self.getNiftiFile('asaxtemp*'))

        # auto-segment the aligned mask object
        f5=Future()
        @taskroutine('Segmenting Aligned Mask')
        def _segmentMask(task=None):
            with f5:
                mask=self.findObject(finalseg)
                numctrls=16
                if isinstance(segobj,SegSceneObject):
                    c=first(segobj.enumContours())
                    if c:
                        numctrls=len(c[0])

                obj=self.Segment.createSegObjectFromMask('Aligned_'+os.path.splitext(origsegname)[0],mask,numctrls,SegmentTypes._LV)
                obj.filename=self.getLocalFile(obj.filename)
                obj.save()
                self.addObject(obj)
                f5.setObject(obj)

        self.mgr.runTasks(_segmentMask(),f5)

        return f1,f2,f3,f4,f3
    
    def alignIntersectImages(self,volume,intersects,tempDir=None,numIters=1,dilation=5,moveScale=0.1):
        
        def calculateVolShifts(vol1,vol2,tempDir):
            with eidolon.processImageNp(vol1) as v1:
                shifts=np.zeros((v1.shape[2],2))
            
                with eidolon.processImageNp(vol2) as v2:
                    for d in range(v1.shape[2]):
                        sx,sy=self.registerImage2D(v1[:,:,d,0],v2[:,:,d,0],tempDir=tempDir,model='Rigid')
                        shifts[d]=-sx.mean(),-sy.mean()
                        
            return shifts.round().astype(np.int32)
    
        tempDir=tempDir or self.mgr.getUserTempDir('alignIntersectImages')
        vdims=volume.getArrayDims()
        vshifts=np.zeros((vdims[2],2))
        ishifts=np.zeros((len(intersects),2))
        
        vclone=volume.clone(volume.getName()+'_aligned') # shifted volume image
        vtarget=volume.clone('vtarget') # register target temporary image
        
        iclones=[i.clone(i.getName()+'_aligned') for i in intersects] # shifted intersecting images
        itargets=[i.clone('itarget') for i in intersects] # register target temporary images
    
        for i in range(numIters):
            # shift the volume image
            
            eidolon.mergeImages(iclones,vtarget) # merge shifted intersect images into volume target
            
            if dilation>0:
                with eidolon.processImageNp(vtarget,True) as im:
                    for d,t in np.ndindex(im.shape[2:]):
                        im[:,:,d,t]=grey_dilation(im[:,:,d,t],dilation)
            
            vs=calculateVolShifts(vclone,vtarget,tempDir) # calculate values to shift volume slices to match target
            vs=vs*moveScale
            
            eidolon.shiftImageXY(vclone,vs)
            vshifts=vshifts+vs
            
            print('Iter',i,np.sqrt(np.sum(vs**2,1)).mean())
            
            # shift each intersection image
            for inter in range(len(intersects)):
                interclone=iclones[inter]
                intertarget=itargets[inter]
                
                eidolon.resampleImage(vclone,intertarget) # resample shifted volume into the target clone for this image
                
                vi=calculateVolShifts(interclone,intertarget,tempDir) # calculate the shift to match target
                vi=vi*moveScale
                
                eidolon.shiftImageXY(interclone,vi)
                ishifts[inter]=ishifts[inter]+vi[0]
                
                print('Iter',i,inter,np.sqrt(np.sum(vi**2,1)).mean())
            
        return vshifts,ishifts

    def rigidRegisterStack(self,subjectname,rtargetname,htargetname,finalname,doffile,paramfile,correctNifti):
        '''
        Determine the rigid registration dof file to register image series `rtargetname' to series `subjectname' then
        apply this registration to series `htargetname' to produce series `finalname'. This will create time registered
        versions of `subjectname' and/or `rtargetname' as needed.
        '''
        cwd=self.getCWD()
        logfile1=self.getLogFile('rreg.log')

        regtarget=rtargetname+'_TRtemp'
        regsubject=subjectname+'_TRtemp'

        targettempnii=self.getNiftiFile(regtarget)
        subjecttempnii=self.getNiftiFile(regsubject)
        subjectnii=self.getNiftiFile(subjectname)
        rtargetnii=self.getNiftiFile(rtargetname)

        if htargetname and finalname:
            htargetnii=self.getNiftiFile(htargetname)
            finalnii=self.getNiftiFile(finalname)

        @taskroutine('Time-registering Images')
        def _timeRegister(task):
            target=self.mgr.findObject(rtargetname) or self.Nifti.loadImage(rtargetnii)
            subject=self.mgr.findObject(subjectname) or self.Nifti.loadImage(subjectnii)

            targetts=len(target.getTimestepList())
            subjectts=len(subject.getTimestepList())

            if targetts<subjectts: # if the target has fewer timesteps, time-register the subject to it
                timeregobj=self.createTimeRegStack(target,subject,regsubject,False)
                self.saveToNifti([timeregobj])
                copyfileSafe(rtargetnii,targettempnii)
            elif targetts>subjectts: # conversely time-register the target to the subject
                timeregobj=self.createTimeRegStack(subject,target,regtarget,False)
                self.saveToNifti([timeregobj])
                copyfileSafe(subjectnii,subjecttempnii)
            else: # otherwise just copy both files to their expected filenames
                copyfileSafe(rtargetnii,targettempnii)
                copyfileSafe(subjectnii,subjecttempnii)


        self.mgr.runTasks(_timeRegister())
        f1=self.mgr.execBatchProgramTask(self.rreg,regtarget+'.nii',regsubject+'.nii','-center','-dofout',doffile,'-parin',paramfile,logfile=logfile1,cwd=cwd)
        self._checkProgramTask(f1)

        self.removeFilesTask(self.getNiftiFile('*_TRtemp*'))

        if htargetname and finalname:
            f2=self.applyImageDof(htargetnii,finalnii,doffile,cwd)
        else:
            f2=None

        return f1,f2

    def rigidRegisterStackList(self,subjectname,intermedname,targetnames):
        '''
        Rigidly register the images in `targetnames' to the image `subjectname'. If `intermedname' is neither "None"
        nor None, determine what the deformation is to rreg this to `subjectname' and apply that deformation to the
        images in `targetnames'. Otherwise determine the deformation for each image in `targetnames' and apply that
        deformation to the image, ie. rreg each image independently using their own image features.
        '''
        assert os.path.isfile(self.getNiftiFile(subjectname)), 'Cannot find %r'%subjectname
        for tn in targetnames:
            assert os.path.isfile(self.getNiftiFile(tn)), 'Cannot find %r'%tn

        if intermedname=='None':
            intermedname=None

        fresult=[]
        filenames=[]
        doffile=None
        cwd=self.getCWD()

        for tn in targetnames:
            finalname=self.getUniqueShortName('RReg',os.path.splitext(tn)[0],'to',os.path.splitext(subjectname)[0])
            finalnii=self.getNiftiFile(finalname)
            filenames.append(finalnii)

            if doffile==None or intermedname==None:
                # If there's no intermediate then compute the deformation independently for each image.
                # If there is an intermediate, this will calculate its deformation field and apply it to `tn'.
                doffile=tn+'.dof'
                ff=self.rigidRegisterStack(subjectname,intermedname or tn,tn,finalname,doffile,self.fixshort,True)
            else:
                # If there's an intermediate and it's dof has be determined, apply it to `tn'.
                # This line is only reached on the second time through the loop with an intermediate.
                ff=self.applyImageDof(self.getNiftiFile(tn),finalnii,doffile,cwd)

            fresult.append(ff)

        fresult.append(self.loadNiftiFiles(filenames))
        return fresult

    def readPolyNodes(self,filename):
        nodes,header=self.VTK.loadPolydataNodes(filename)
        nodes.mul(vec3(-1,-1,1))
        return nodes,header

    def writePolyNodes(self,filename,nodes):
        return self.VTK.savePolydataNodes(filename,nodes,lambda v:(-v.x(),-v.y(),v.z()))

    def createImageGrid(self,obj,w,h,d):
        f=Future()

        @taskroutine('Creating Grid')
        def _createGrid(obj,w,h,d,task):
            with f:
                obj=self.findObject(obj)
                name=self.getUniqueShortName(obj.getName(),'Grid')
                filename=self.getLocalFile(name+'.vtk')
                nodes,inds=eidolon.generateHexBox(w,h,d)

                ds=eidolon.PyDataSet(obj.getName()+'DS',nodes,[('inds',eidolon.ElemType._Hex1NL,inds)])
                ds.getNodes().mul(obj.getVolumeTransform())

                obj= MeshSceneObject(name,ds,self.VTK,filename=filename)
                self.VTK.saveObject(obj,filename)
                self.addObject(obj)
                f.setObject(obj)

        return self.mgr.runTasks([_createGrid(obj,w,h,d)],f,False)

    @taskmethod('Creating Isotropic Object')
    def createIsotropicObject(self,obj,cropEmpty,spacing=1.0,task=None):
        obj=self.findObject(obj)

        outname=self.getUniqueShortName(obj.getName(),'Iso')
        outfile=self.getNiftiFile(outname)

        if cropEmpty:
            obj=self.emptyCropObject(obj,False)

        isoobj=obj.plugin.createRespacedObject(obj,obj.getName()+'_Iso',vec3(spacing))
        eidolon.resampleImage(obj,isoobj)
        isoobj.plugin.saveObject(isoobj,outfile,setFilenames=True)
        self.addObject(isoobj)

        return isoobj

    @taskmethod('Setting Timestep')
    def setObjectTimestep(self,objname,start,step,task=None):
        obj=self.findObject(objname)

        obj.setTimestepScheme(start,step)

        if isinstance(obj,ImageSceneObject):
            obj.proptuples=[]
            self.saveToNifti([obj])

        return obj

    def invertTimesteps(self,sourceobj):
        sourceobj=self.findObject(sourceobj)
        assert sourceobj.isTimeDependent
        timesteps=sourceobj.getTimestepIndices()
        images=[]

        for i in range(len(timesteps)):
            ts=timesteps[i][0]
            for ind in timesteps[-i-1][1]:
                image=sourceobj.images[ind].clone()
                image.timestep=ts
                images.append(image)

        nobj=ImageSceneObject(sourceobj.getName()+'_swap',sourceobj.source,images,sourceobj.plugin,True)

        self.saveToNifti([nobj])
        self.addObject(nobj)
        return nobj

    def offsetTimesteps(self,sourceobj,suffix,value,makeProspective=False):
        sourceobj=self.findObject(sourceobj)

        if makeProspective:
            timesteps=sourceobj.getTimestepList()
            avgdiff=eidolon.avgspan(timesteps)
            value=avgdiff/2

        for i in sourceobj.images:
            i.timestep+=value

        sourceobj.setName(sourceobj.getName()+suffix)
        sourceobj.source=None # prevent the project from asking whether to delete this file

        self.mgr.removeSceneObject(sourceobj)
        self.saveToNifti([sourceobj])

        return self.loadNiftiFiles([self.getNiftiFile(sourceobj.getName())])

    def resampleObject(self,srcname,templatename,isIsotropic):
        f=Future()
        @taskroutine('Resampling Image')
        def _resample(srcname,templatename,isIsotropic,task):
            with f:
                obj=self.findObject(srcname)
                tmplt=self.findObject(templatename)

                name=self.getUniqueShortName(templatename,'Res')
                reobj=tmplt.plugin.extractTimesteps(tmplt,name,timesteps=obj.getTimestepList())

                if isIsotropic:
                    tslist=reobj.getTimestepList()
                    reobj=reobj.plugin.createIntersectObject(name,[reobj,obj],len(tslist),vec3(min(obj.getVoxelSize())))
                    reobj.setTimestepList(tslist)

                eidolon.resampleImage(obj,reobj)

                filename=self.saveToNifti([reobj])
                f.setObject(self.loadNiftiFiles(filename))

        return self.mgr.runTasks(_resample(srcname,templatename,isIsotropic),f)

    def extractTimestepsToObject(self,srcname,indices=None,timesteps=None):
        f=Future()
        @taskroutine('Extracting Timesteps')
        def _extract(srcname,indices,timesteps,task):
            with f:
                obj=self.findObject(srcname)

                name=self.getUniqueShortName(obj.getName(),'Extr')
                extrobj=obj.plugin.extractTimesteps(obj,name,indices,timesteps)

                filename=self.saveToNifti([extrobj])
                f.setObject(self.loadNiftiFiles(filename))

        return self.mgr.runTasks(_extract(srcname,indices,timesteps),f)

    @taskmethod('Reorder Multicycle Image')
    def reorderMulticycleImage(self,srcname,starttime,timestep,task):
        obj=self.findObject(srcname)
        timeinds=obj.getTimestepIndices()
        startind=min((abs(timeinds[i][0]-starttime),i) for i in range(len(timeinds)))[1]
        rinds=eidolon.rotateIndices(startind,len(timeinds))
        images=[]

        for i,ri in enumerate(rinds):
            for ind in timeinds[ri][1]:
                img=obj.images[ind].clone()
                img.timestep=i*timestep
                images.append(img)

        name=self.getUniqueShortName(obj.getName(),'Reord')
        reobj=ImageSceneObject(name,obj.source,images,obj.plugin)

        filename=self.saveToNifti([reobj])
        return self.loadNiftiFiles(filename)

    @taskmethod('Cropping object')
    def cropMotionObject(self,srcname,threshold,filtersize,task):
        imgobj=self.findObject(srcname)
        name=self.getUniqueShortName(srcname,'Crop')
        cobj=eidolon.cropMotionImage(imgobj,name,threshold,filtersize)
        filename=self.saveToNifti([cobj])
        return self.loadNiftiFiles(filename)
    
    def emptyCropObject(self,imgobj,loadObj=True):
        f=Future()
        @taskroutine('Empty Space-cropping Image Object')
        def _crop(imgobj,loadObj,task):
            with f:
                imgobj=self.findObject(imgobj)

                cropname=self.getUniqueShortName(imgobj.getName(),'Crop')
                cobj=eidolon.cropObjectEmptySpace(imgobj,cropname,20,False)
                if loadObj:
                    f.setObject(self.saveToNifti([cobj]))
                else:
                    f.setObject(cobj)

        ff=self.mgr.runTasks(_crop(imgobj,loadObj),f)
        if loadObj:
            return self.loadNiftiFiles(f)
        else:
            return ff

    def refImageCrop(self,imgname,refname,mx,my):
        f=Future()
        @taskroutine('Boundbox-cropping Image Object')
        def _crop(imgname,refname,mx,my,task):
            with f:
                cropname=self.getUniqueShortName(imgname,'Crop',complen=20)

                imgobj=self.findObject(imgname)
                ref=self.findObject(refname)
                cropobj=eidolon.cropRefImage(imgobj,ref,cropname,mx,my)
                self.addObject(cropobj)

                f.setObject(self.saveToNifti([cropobj],True))

        return self.mgr.runTasks([_crop(imgname,refname,mx,my)],f)

    def extendImageStack(self,stack,mx=0,my=0,mz=0,value=0):
        '''
        Given image stack named by `stack', extend the images by `mx' and `my' and add `mz' images on the above and
        below the stack. The new image areas are filled with `value'. This returns the extend object and a list with
        the NIfTI filename it was saved to.
        '''
        obj=self.findObject(stack)
        ext=extendImage(obj,self.getUniqueShortName(obj.getName(),'Ext'),mx,my,mz,value)
        return ext,self.saveToNifti([ext],True)

    @taskmethod('Extending image object')
    def extendImageObject(self,obj,mx=0,my=0,mz=0,value=0,task=None):
        '''
        Given image object or name `obj', extend the images by `mx' and `my' and add `mz' images on the above and
        below the stack. The new image areas are filled with `value'. This returns a Future containing the object
        added to the scene. This differs from extendImageStack() by adding the new object to the scene rather than
        just returning it and saving it to a NIfTI file, as well as being implemented as a task method.
        '''
        obj=self.findObject(obj)
        ext=extendImage(obj,self.getUniqueShortName(obj.getName(),'Ext'),mx,my,mz,value)
        self.saveToNifti([ext],True)
        self.addObject(ext)
        return ext
    
    def registerImage2D(self,src,tgt,tempDir=None,spacing=10,model='BSplineFFD'):
        '''
        Register the 2D image `src` to `tgt`, returning the X and Y deformation fields to do so. The `tmpdir` directory 
        path is used for temporary information. The `plugin` object is expected to be an IRTK plugin instance. The 
        `spacing` value specifies the spacing between control points. The `model` field is either 'BSplineFFD' or 
        'Rigid' to specify the deformation model.
        '''
        def _run(*cmd):
            cmd=tuple(str(c) for c in cmd)
            rcode,stdout=execBatchProgram(*cmd,cwd=tempDir)
            assert rcode==0,'Error: %r %r:\n%s'%(rcode,cmd,stdout)
            return stdout
            
        tempDir=tempDir or self.mgr.getUserTempDir('tmp_interpolate')
        
        self.Nifti.writeImageData(src,os.path.join(tempDir,'src.nii'))
        self.Nifti.writeImageData(tgt,os.path.join(tempDir,'tgt.nii'))
        
        _run(self.register,'tgt.nii','src.nii','-dofout','src-tgt.dof',
             '-parout','reg.cfg',
             '-par','Control point spacing',spacing,
             '-par','Transformation model',model,
             '-par','Allow rotations','Yes' if model!='Rigid' else 'No'
            )
        
        if model=='Rigid':
            _run(self.convertdof,'src-tgt.dof','src-tgt.txt','-target','src.nii')  
        else:
            _run(self.convertdof,'src-tgt.dof','src-tgt.txt')
        
#             _run(plugin.convertdof,'src-tgt.dof','src-tgt.nii','-format','nreg')
        
        dof=np.loadtxt(os.path.join(tempDir,'src-tgt.txt'),skiprows=1)
        
        # determine the dimensions of the deformation lattice which has the same aspect ratio as src
        w,h=src.shape
        ratio=dof.shape[0]/(w*h)
        wd=int((h*ratio**0.5))
        hd=dof.shape[0]//wd
    
        # resize the X and Y deformation components by the spacing value and crop the center
        x=zoom(dof[:,3].reshape((wd,hd)).T,spacing)
        x=cropCenter(x,*src.shape)
        y=zoom(dof[:,4].reshape((wd,hd)).T,spacing)
        y=cropCenter(y,*src.shape)
        
        return x,y
    
    def interpolateImages2D(self,im0,im1,numImgs,tempDir=None):
        '''Generate an interpolation stack between 2D images `im0` and `im1` with `numImgs' total number of images.'''
        assert numImgs>2
        
        tempDir=tempDir or self.mgr.getUserTempDir('tmp_interpolate')
        
        rx01,ry01=self.registerImage2D(im0,im1,tempDir)
        rx10,ry10=self.registerImage2D(im1,im0,tempDir)
        
        out=np.zeros(tuple(im0.shape)+(numImgs,),dtype=im0.dtype)
        
        out[...,0]=im0
        out[...,-1]=im1
        
        for i in range(1,numImgs-1):
            z=i/numImgs
            iz=1.0-z
            out[...,i]=deformImage2D(im0*iz,rx01*z,ry01*z)+deformImage2D(im1*z,rx10*iz,ry10*iz)
        
        return out
    
    @taskmethod('Interpolating image object')
    def interpolateImageObject(self,obj,numAddedSlices,tempDir=None,task=None):
        tempDir=tempDir or self.mgr.getUserTempDir('tmp_interpolate')
        
        w,h,d,t=obj.getArrayDims()
        trans=obj.getVolumeTransform()
        scale=trans.getScale().abs()
        numslices=d+(d-1)*numAddedSlices
        skip=numAddedSlices+1
        
        spacing=scale/eidolon.vec3(w,h,numslices)
        
        out=obj.createRespacedObject(obj.getName()+'_Interp',spacing)
        
        with eidolon.processImageNp(obj) as imobj:
            with eidolon.processImageNp(out,True) as imout:
                for ts in range(t):
                    for i in range(d-1):
                        im0=imobj[:,:,i,ts]
                        im1=imobj[:,:,i+1,ts]
                        interp=self.interpolateImages2D(im0,im1,numAddedSlices+2,tempDir)
                        
                        imout[:,:,i*skip:i*skip+numAddedSlices+2,ts]=interp
                
        return out

    def applyMotionTrack(self,obj_or_name,trackname_or_dir,addObject=True):
        '''
        Apply the motion track data in `trackname_or_dir' to `obj_or_name'. The value `obj_or_name' is either a mesh
        or image SceneObject, or the name of one in the current context. The value `trackname_or_dir' is the path
        to a directory containing tracking information or the name of one in the current context. If `addObject' is
        True then the resulting SceneObject produced by applying the tracking information is added to the current
        context. Return value is the time-dependent SceneObject containing the tracking information, or a Future
        containing this object if the method was called outside of the task thread.
        '''
        obj=self.findObject(obj_or_name)

        if os.path.isdir(trackname_or_dir):
            trackdir=os.path.abspath(trackname_or_dir)
        else:
            trackdir=self.getLocalFile(trackname_or_dir)

        conf=readBasicConfig(os.path.join(trackdir,trackconfname))
        timesteps=conf[JobMetaValues._timesteps]
        trackfiles=sorted(glob.glob(os.path.join(trackdir,'*.dof*')))
        isSingleDof=len(trackfiles)==1
        isFrameByFrame=conf[JobMetaValues._tracktype] in (TrackTypes._gpunreg,TrackTypes._mirtkregister) and not isSingleDof
        resultname=self.getUniqueShortName(obj.getName(),'Tracked',trackname_or_dir)
        f=Future()
        
        assert isinstance(obj,(ImageSceneObject,MeshSceneObject))
        assert trackfiles

        if isinstance(obj,MeshSceneObject):
            # single dof file for multiple timesteps rather than on file per step
            if len(trackfiles)==1:
                trackfiles=[trackfiles[0]]*(len(timesteps)-1)

            # read the times data so that ptransformation can be set to the right timestep
            if os.path.isfile(os.path.join(trackdir,'times.txt')):
                with open(os.path.join(trackdir,'times.txt')) as o:
                    times=list(map(float,o.readlines()))
            elif isSingleDof:
                times=timesteps
            else:
                times=[-1]*len(trackfiles)

            assert len(timesteps)==len(trackfiles)+1,'%i != %i'%(len(timesteps),len(trackfiles)+1)

            self.writePolyNodes(os.path.join(trackdir,'in.vtk'),obj.datasets[0].getNodes())

            filelists=[('in.vtk','out%.4i.vtk'%i,dof,times[i]) for i,dof in enumerate(trackfiles)]
            self.mgr.runTasks(applyMotionTrackTask(self.transpts,trackdir,False,filelists,['-ascii'])) # apply transforms

            @taskroutine('Loading Tracked Files')
            def _loadSeq(obj,outfiles,timesteps,name,task):
                with f:
                    filenames=[os.path.join(trackdir,o) for o in outfiles]

                    objds=obj.datasets[0]

                    dds=[objds.clone(objds.getName()+'clone0',True,True,True)]

                    indices=list(dds[0].enumIndexSets())
                    fields=list(dds[0].enumDataFields())

                    for i,ff in enumerate(filenames):
                        nodes,_=self.readPolyNodes(ff)
                        dds.append(eidolon.PyDataSet('%sclone%i'%(objds.getName(),i+1),nodes,indices,fields))

                    # if the dofs are frame-by-frame transformations, rejig the node data to reflect this transformation
                    # since the default is assuming each dof is the transformation from frame 0 to frame n
                    if isFrameByFrame:
                        n0=dds[0].getNodes()
                        for i in range(1,len(dds)):
                            n=dds[i].getNodes()
                            n.sub(n0)
                            n.add(dds[i-1].getNodes())

                    result=MeshSceneObject(name,dds,filenames=filenames)
                    result.setTimestepList(timesteps)

                    if addObject:
                        # attempt to save the object with its own plugin, defaulting to VTK if this doesn't work
                        try:
                            obj.plugin.saveObject(result,self.getLocalFile(name),setFilenames=True)
                        except ValueError:
                            self.VTK.saveObject(result,self.getLocalFile(name),setFilenames=True)
                        except NotImplementedError:
                            self.VTK.saveObject(result,self.getLocalFile(name),setFilenames=True)

                        self.addObject(result)

                    f.setObject(result)

            return self.mgr.runTasks(_loadSeq(obj,[ff[1] for ff in filelists],timesteps,resultname),f)
        else:
#            assert not isFrameByFrame,'Frame-by-frame not supported for images yet'

            #objnii=self.getNiftiFile(obj.getName())
            objnii=obj.getObjFiles()[0]
            resultnii=self.getNiftiFile(resultname)
            numProcs=0
            
            if isFrameByFrame:
                filelists=[]
                mergeddofs=[trackfiles[0]]
                
                for i in range(2,len(trackfiles)+1):
                    os.makedirs(os.path.join(trackdir,'merged'),exist_ok=True)
                    outfile=os.path.join('merged','merged%.4i.dof.gz'%(i-1))
                    logfile=os.path.join('merged','merged%.4i.log'%(i-1))
                    mergeddofs.append(outfile)
                    args=list(trackfiles[:i])+[outfile]
                    r=execBatchProgram(self.composedofs,*args,cwd=trackdir,logfile=logfile)
                    
                    if r[0]:
                        raise IOError('Dof merge failed on step %i'%i)
                        
                trackfiles=mergeddofs
                
            filelists=[(objnii,'out%.4i.nii'%i,dof,-1) for i,dof in enumerate(trackfiles)]
                
            self.mgr.runTasks(applyMotionTrackTask(self.transimage,trackdir,True,filelists,numProcs=numProcs))

            @taskroutine('Loading Tracked Files')
            def _loadSeq(task):
                with f:
                    objs=[self.Nifti.loadObject(os.path.join(trackdir,fl[1])) for fl in filelists]
                    result=self.Nifti.createSequence(resultname,objs,timesteps)
                    self.Nifti.saveObject(result,resultnii,setFilenames=True)
                    self.mgr.addSceneObject(result)

                    if addObject:
                        self.addObject(result)

                    f.setObject(result)

            return self.mgr.runTasks(_loadSeq(),f)

    @timing
    def applyMotionTrackPoints(self,dirname,pts):
        '''
        Simple synchronous method applying the motion track data in `dirname' to the list of vec3 points `pts'.
        Returns map of timesteps to motion tracked points at those times. This method blocks while the tracking
        is applied to the points so it shouldn't be expected to be instantaneous.
        '''
        initobj=MeshSceneObject('proxy',eidolon.PyDataSet('proxyds',pts))
        f=self.applyMotionTrack(initobj,dirname,False)
        trackobj=Future.get(f,None)
        return {ts:ds.getNodes()[:,0] for ts,ds in zip(trackobj.getTimestepList(),trackobj.datasets)}

    def isServerAlive(self,serveraddr=None,serverport=None):
        '''
        Attempts to connect to the server, if this fails the server isn't running or isn't accessible so return False.
        If `serveraddr' or `serverport' are given, these values are used instead of those given by getServerAddrPort().
        '''
        try:
            addr,port=self.getServerAddrPort()

            s=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
            s.connect((serveraddr or addr,serverport or port)) # throws an exception if the server isn't started
            s.close()
            return True
        except:
            return False

    def sendServerMsg(self,msg,args=(),buffsize=4096,timeout=10.0,serveraddr=None,serverport=None):
        '''Sends a message to a currently running server.'''
        assert msg in ServerMsgs, 'Unknown message %r'%msg
        assert all(a==None or isinstance(a,t) for a,t in zip(args,ServerMsgs[msg][0])), 'Arguments do not have type '+repr(ServerMsgs[msg][0])

        addr,port=self.getServerAddrPort()

        with closing(socket.socket(socket.AF_INET,socket.SOCK_STREAM)) as s: # ensure s.close() is called when the block exits for any reason
            s.settimeout(timeout)
            s.connect((serveraddr or addr,serverport or port)) # connect using addr:port arguments or those given by getServerAddrPort()
            s.sendall(pickle.dumps((msg,args))) # send the pickled message pair
            s.shutdown(socket.SHUT_WR) # let server know we've sent all we're going to send
            received=''
            res=None
            while res==None or len(res)==buffsize: # read the response in `buffsize' chunks
                res=s.recv(buffsize)
                received+=res

            return pickle.loads(received) # return the unpickled response

    def startMotionTrackServer(self,addr=None,port=None):
        '''Starts the server on the local machine if it isn't running and returns the process object, does nothing otherwise.'''

        # TODO: need to fix this, the processes aren't spawning correctly, especially in packed app form, need to spawn new copy of eidolon and run from there

        if not addr or not port:
            addr,port=self.getServerAddrPort()

        newport=port
        startserver=False

        # Check to see if there's a server running at addr:port that was started by the current user, if so then use it,
        # otherwise increment port and check again. Once an unused port number if found, use this to start a new server.
        while not startserver:
            try:
                name,msg=self.sendServerMsg(ServerMsgs._Check,serveraddr=addr,serverport=newport) # throws an exception if the server isn't started
                if msg[0]==eidolon.getUsername(): # if this server is run by the current user, use it
                    break
                else:
                    newport+=1 # otherwise increment the port number
            except:
                startserver=True # can't connect so start a new server with this port

        if startserver or newport!=port: # save the address and port if it's changed
            self.setServerAddrPort('localhost' if startserver else addr,newport)

        if startserver: # if we can't find a server run by the current user, start one locally
            return self.mgr.callThreadSafe(MotionTrackServerDialog,self.serverdir,newport,self.motiontrack)
#           scriptfile=inspect.getfile(inspect.currentframe())
#           logfile=self.mgr.getUserAppFile('motionserver.log')
#           args=[sys.executable,'-s',scriptfile,self.serverdir,str(newport),self.motiontrack]
#           proc=subprocess.Popen(args,stderr = subprocess.STDOUT, stdout=open(logfile,'w'), close_fds=not isWindows)
#           time.sleep(5) # wait for the program to launch, especially in OSX which is slow to do anything
#           return proc

#       msp=MotionServerProcess(self.serverdir,newport,self.motiontrack)
#       msp.start()
#       time.sleep(5) # wait for the program to launch, especially in OSX which is slow to do anything
#       return msp

    def startMotionTrackJob(self,trackname,maskname,dirname,adaptive,chosenparam):
        f=Future()
        @taskroutine('Starting Motion Track Job')
        def _startJob(trackname,maskname,dirname,adaptive,chosenparam,task):
            with f:
                trackobj=self.findObject(trackname)
                timesteps=trackobj.getTimestepList()
                isTagged='tagged' in trackname
                paramfile=self.patient1e6 if isTagged else self.patient1e4

                conf={
                    JobMetaValues._trackobj     :trackname,
                    JobMetaValues._maskobj      :maskname,
                    JobMetaValues._tracktype    :TrackTypes._motiontrackmultimage,
                    JobMetaValues._timesteps    :timesteps,
                    JobMetaValues._numtrackfiles:len(timesteps)-1,
                    JobMetaValues._transform    :tuple(trackobj.getVolumeTransform()),
                    JobMetaValues._pixdim       :tuple(trackobj.getVoxelSize()),
                }

                if chosenparam and os.path.isfile(chosenparam):
                    paramfile=chosenparam

                assert trackobj!=None,'Cannot find object '+trackname

                if not isTagged:
                    trackfile=self.extendImageStack(trackname,mz=4)[1][0]
                    #self._checkProgramTask(f1)
                else:
                    trackfile=self.getNiftiFile(trackname)

                if maskname!=None:
                    mask=self.findObject(maskname)
                    maski=trackobj.plugin.extractTimesteps(trackobj,maskname+'I',timesteps=[0])
                    eidolon.resampleImage(mask,maski)
                    maskfile=self.extendImageStack(maski,mz=4)[1][0]
                    #self._checkProgramTask(f2)
                else:
                    maskfile=None

                if not os.path.exists(paramfile):
                    paramfile=self.patient1e6 if isTagged else self.patient1e4

                #if dirname:
                #   dirname=self.getUniqueObjName(dirname)

                msg=[True,None,trackfile,maskfile,paramfile,dirname,adaptive,conf,self.getCWD()]

                self.startMotionTrackServer()

                f.setObject(self.sendServerMsg(ServerMsgs._StartMotionTrack,msg))

        return self.mgr.runTasks(_startJob(trackname,maskname,dirname,adaptive,chosenparam),f,False)

    def startGPUNRegMotionTrack(self,imgname,maskname,trackname,paramfile):
        f=Future()
        @taskroutine('Tracking Image With GPU NReg')
        @timing
        def _GPUTrack(imgname,maskname,trackname,paramfile,task):
            with f:
                if not isLinux:
                    raise Exception('GPU NReg is Linux only')

                imgobj=self.mgr.findObject(imgname)
                indices=imgobj.getTimestepIndices()
                timesteps=imgobj.getTimestepList()

                if not os.path.isfile(paramfile):
                    paramfile=self.gpu_nreg_default

                trackname=trackname.strip() or 'GPUNRegTrack_'+imgobj.getName()

                trackname=self.getUniqueObjName(trackname)
                trackdir=self.getLocalFile(trackname)
                maskfile=None

                if maskname and maskname!='None':
                    mask=self.findObject(maskname)
                    maski=imgobj.plugin.extractTimesteps(imgobj,maskname+'I',timesteps=[0])
                    eidolon.resampleImage(mask,maski)
                    maskfile=self.getUniqueLocalFile(maskname+'_I')
                    self.Nifti.saveObject(maski,maskfile)

                os.mkdir(trackdir)
                names=[]
                results=[]

                conf={
                    JobMetaValues._trackobj     :imgname,
                    JobMetaValues._maskobj      :maskname,
                    JobMetaValues._resultcode   :None,
                    JobMetaValues._numtrackfiles:len(timesteps)-1,
                    JobMetaValues._tracktype    :TrackTypes._gpunreg,
                    JobMetaValues._timesteps    :timesteps,
                    JobMetaValues._transform    :tuple(imgobj.getVolumeTransform()),
                    JobMetaValues._pixdim       :tuple(imgobj.getVoxelSize()),
                    JobMetaValues._trackfile    :trackname,
                    JobMetaValues._paramfile    :paramfile,
                    JobMetaValues._maskfile     :maskname,
                    JobMetaValues._startdate    :time.asctime()
                }

                eidolon.storeBasicConfig(os.path.join(trackdir,trackconfname),conf)

#               # dilate mask
#               if os.path.isfile(maskfile):
#                   maskfile=os.path.join(trackdir,'mask.nii')
#                   maskobj=self.mgr.findObject(maskname).clone('mask')
#                   dilateImageVolume(maskobj,(10,10,10))
#                   self.Nifti.saveObject(maskobj,maskfile)

                for i,tsinds in enumerate(indices):
                    name='image%.4i'%i
                    filename=os.path.join(trackdir,name+'.nii')
                    names.append(filename)
                    subobj=ImageSceneObject(name,imgobj.source,eidolon.indexList(tsinds[1],imgobj.images),imgobj.plugin,False)
                    self.Nifti.saveObject(subobj,filename)

                task.setMaxProgress(len(names)-1)
                task.setLabel('Tracking Image With GPU NReg')

                for i,(img1,img2) in enumerate(eidolon.successive(names)):
                    logfile=os.path.join(trackdir,'%.4i.log'%i)
                    args=[img1,img2,'-parin',paramfile,'-dofout','%.4i.dof.gz'%i]
                    if maskfile and os.path.isfile(maskfile):
                        args+=['-mask',maskfile]
                    r=execBatchProgram(self.gpu_nreg,*args,cwd=trackdir,logfile=logfile)
                    results.append(r)
                    task.setProgress(i+1)

                    if r[0]:
                        raise IOError('GPU nreg failed with error code %i (%s)'%r)

                f.setObject(results)

        return self.mgr.runTasks(_GPUTrack(imgname,maskname,trackname,paramfile),f,False)

    @taskmethod('Tracking Image With MIRTK register')
    @timing
    def startRegisterMotionTrack(self,imgname,maskname,trackname,paramfile,model=None,onefile=False,task=None):
        '''Motion tracking using MIRTK register program.'''
        imgobj=self.mgr.findObject(imgname)
        indices=imgobj.getTimestepIndices()
        timesteps=imgobj.getTimestepList()
        model=model or 'FFD'

        if not os.path.isfile(paramfile): # choose the default parameter file if no valid one provided
            paramfile=self.ffd_motion

        trackname=trackname.strip() or 'RegTrack_'+imgobj.getName() # choose default track name based on image object name

        trackname=self.getUniqueObjName(trackname)
        trackdir=self.getLocalFile(trackname)
        maskfile=None
        results=[]

        os.mkdir(trackdir) # create the directory to contain all the tracking information

        shutil.copy(paramfile,os.path.join(trackdir,'original.cfg')) # copy the original param file into the directory as well

        # if a mask object is provided, reimage it to the same space as the tracked image and save to the tracking directory
        if maskname and maskname!='None':
            mask=self.findObject(maskname)
            maskfile=os.path.join(trackdir,maskname+'_I') #self.getUniqueLocalFile(maskname+'_I')
            maski=imgobj.plugin.extractTimesteps(imgobj,maskname+'I',timesteps=[0])
            eidolon.resampleImage(mask,maski)
            self.Nifti.saveObject(maski,maskfile)
            task.setLabel('Tracking Image With MIRTK register') # reset the label

        # initialize the configuration values to store in the tracking ini file
        conf={
            JobMetaValues._trackobj     :imgname,
            JobMetaValues._maskobj      :maskname,
            JobMetaValues._resultcode   :None,
            JobMetaValues._numtrackfiles:len(timesteps)-1,
            JobMetaValues._tracktype    :TrackTypes._mirtkregister1file if onefile else TrackTypes._mirtkregister,
            JobMetaValues._timesteps    :timesteps,
            JobMetaValues._transform    :tuple(imgobj.getVolumeTransform()),
            JobMetaValues._pixdim       :tuple(imgobj.getVoxelSize()),
            JobMetaValues._trackfile    :trackname,
            JobMetaValues._paramfile    :paramfile,
            JobMetaValues._maskfile     :maskfile,
            JobMetaValues._startdate    :time.asctime(),
            JobMetaValues._enddate      :None
        }

        eidolon.storeBasicConfig(os.path.join(trackdir,trackconfname),conf) # store initial config values in the tracking ini file

        if onefile:
            logfile=os.path.join(trackdir,'track.log')
            args=[imgobj.source['filename'],'-parin',paramfile,'-model',model,'-dofout','track.dof.gz','-parout','register.cfg']
            if maskfile and os.path.isfile(maskfile): # add the mask parameter if present
                args+=['-mask',maskfile]

            task.setMaxProgress(1)
            task.setProgress(0)
            r=execBatchProgram(self.register,*args,cwd=trackdir,logfile=logfile)
            results.append(r)
            task.setProgress(1)
        else:
            names=[]
            # save each timestep into a separate nifti file
            for i,tsinds in enumerate(indices):
                name='image%.4i'%i
                filename=os.path.join(trackdir,name+'.nii')
                names.append(filename)
                subobj=ImageSceneObject(name,imgobj.source,eidolon.indexList(tsinds[1],imgobj.images),imgobj.plugin,False)
                self.Nifti.saveObject(subobj,filename)

            task.setMaxProgress(len(names)-1)

            # iterate over every successive timestep pairing and run register
            for i,(img1,img2) in enumerate(eidolon.successive(names)):
                logfile=os.path.join(trackdir,'%.4i.log'%i)
                args=[img1,img2,'-parin',paramfile,'-model',model,'-dofout','%.4i.dof.gz'%i]

                if maskfile and os.path.isfile(maskfile): # add the mask parameter if present
                    args+=['-mask',maskfile]

                if i==0: # spit out the parameter file for the first invocation so that config values are preserved for later inspection
                    args+=['-parout',os.path.join(trackdir,'register.cfg')]

                r=execBatchProgram(self.register,*args,cwd=trackdir,logfile=logfile)
                results.append(r)
                task.setProgress(i+1)

                if r[0]: # stop immediately if register failed
                    break

        # store the result code and end date in the tracking ini file
        conf[JobMetaValues._resultcode]=results[-1][0]
        conf[JobMetaValues._enddate]=time.asctime()
        eidolon.storeBasicConfig(os.path.join(trackdir,trackconfname),conf)

        if results[-1][0]:
            raise IOError('register failed with error code %i:\n%s'%results[-1])

        return results

    def checkMotionTrackJobs(self,jids):
        f=Future()
        assert all(isinstance(jid,int) for jid in jids)

        @taskroutine('Checking Jobs')
        def _checkJobs(jids,task):
            with f:
                results=[]
                deadjobs=[]

                for jid in jids:
                    name,msg=self.sendServerMsg(ServerMsgs._Stat,(jid,))

                    assert name in (ServerMsgs._Except,ServerMsgs._RStat)
                    rcode=None

                    if name==ServerMsgs._Except:
                        self.mgr.showExcept(msg[1],'MotionTrackServer reported an exception when requesting job status.','Exception from Server')
                    else:
                        rcode,num,total,jobdir=msg
                        trackfile='???'
                        trackdir=self.getLocalFile(os.path.basename(jobdir))
                        inifile=os.path.join(trackdir,trackconfname)

                        if os.path.isfile(inifile):
                            conf=readBasicConfig(inifile)
                            trackfile=os.path.split(conf[JobMetaValues._trackfile])[1]

                        if rcode==-1 and total==0:
                            stat='Unknown Job'
                            deadjobs.append(jid)
                        elif rcode==0:
                            stat='Done, Results in directory motiontrack%i'% jid
                        elif rcode==None:
                            stat='Running, Progress: %i%%'%int(round(100.0*num/float(total)))
                        else:
                            stat='Failed, Exit code: %i'%rcode

                        stat+=' (Job ID: %i, trackfile: %s)'%(jid,trackfile)
                        results.append(stat)

                    if rcode==0:
                        name,msg=self.sendServerMsg(ServerMsgs._GetResult,(jid,True))
                        if name==ServerMsgs._Except:
                            self.mgr.showExcept(msg[1],'MotionTrackServer reported an exception when requesting job results.','Exception from Server')

                        # TODO: for now do nothing when a job completes correctly since the local files are in the project dir
#                       else:
#                           os.mkdir(self.project.getProjectFile('motiontrack%s'%str(jid).zfill(3)))
#                           for i,ff in enumerate(msg[0]):
#                               name=self.getProjectFile('%s/%s.dof.gz'%(str(jid).zfill(3),str(i).zfill(3)))
#                               copyfileSafe(ff,name)
#
#                           #self.configMap[ConfigNames._jobids].pop(jid)
#                           #self.saveConfig()

                f.setObject((results,deadjobs))

        return self.mgr.runTasks(_checkJobs(jids),f,False)


class MotionTrackServerWidget(QtWidgets.QWidget,Ui_mtServerForm):
    def __init__(self,serverdir,serverport,motiontrackpath):
        QtWidgets.QWidget.__init__(self)
        self.setupUi(self)

        self.serverdir=serverdir
        self.jidfile=os.path.join(self.serverdir,'motion_jid.txt')
        self.serverport=int(serverport)
        self.motiontrackpath=motiontrackpath
        self.username=eidolon.getUsername()
        self.runningProcs=[] # list of (Subprocess,jid,directory) triples

        if not os.path.exists(self.serverdir):
            os.mkdir(self.serverdir)

        if not os.path.exists(self.jidfile):
            self.setJID(1)

        class MotionTrackHandler(socketserver.StreamRequestHandler):
            def handle(hself):
                self.handleRequest(hself.rfile,hself.wfile)

        self.server = socketserver.TCPServer(('localhost', self.serverport), MotionTrackHandler)
        self.serverThread=threading.Thread(target=self.server.serve_forever)
        self.serverThread.start()

        self.killButton.clicked.connect(self._killJob)

        self.timer=eidolon.QtCore.QTimer()
        self.timer.timeout.connect(self._updateList)
        self.timer.start(3000)

    def getJID(self):
        with open(self.jidfile) as o:
            return int(o.read().strip())

    def setJID(self,jid):
        with open(self.jidfile,'w') as o: # obviously racy but the probability of 2 simultaneous writes is incredibly low
            o.write(str(jid)+'\n')

    def _updateList(self):
        statlist=[]

        for proc,jid,jobdir in self.runningProcs:
            pid=proc.pid
#           jobdir=os.path.join(jdir,'motiontrack%i'%jid)
            conffile=os.path.join(jobdir,trackconfname)
            conf=readBasicConfig(conffile)

            rcode=conf[JobMetaValues._resultcode]
            numTF=conf[JobMetaValues._numtrackfiles]

            numfiles=len(glob.glob(os.path.join(jobdir,'*.dof*')))

            rcode=rcode if rcode!=None else proc.poll()

            if rcode!=None and conf[JobMetaValues._resultcode]==None: # update the stored result if necessary
                conf[JobMetaValues._resultcode]=rcode
                eidolon.storeBasicConfig(conffile,conf)

            stat='Job %i, Status: '%jid
            if rcode==None:
                stat+='Running'
            elif rcode==0:
                stat+='Completed'
            else:
                stat+='Failed, Result: %i'%rcode

            stat+=', PID: %i, Progress: %i%% (%i/%i files)'%(pid,int(round(100.0*numfiles/float(numTF))),numfiles,numTF)

            statlist.append(stat)

        eidolon.fillList(self.jobList,statlist,self.jobList.currentRow())

    def _killJob(self):
        ind=self.jobList.currentRow()
        if ind>=0:
            msg='This kills the tracking job, are you sure?'
            reply = QtWidgets.QMessageBox.question(self, 'Kill Job', msg, QtWidgets.QMessageBox.Yes, QtWidgets.QMessageBox.No)
            if reply == QtWidgets.QMessageBox.Yes:
                proc=self.runningProcs[ind][0]
                proc.kill()

    def stopServer(self):
        self.server.shutdown()

        for proc,jid,jdir in self.runningProcs:
            if proc.returncode==None:
                proc.kill()

    def handleRequest(self,rfile,wfile):
        try:
            msg,args=pickle.loads(rfile.read())

            if msg==ServerMsgs._Check: # check message, returns the username who started this server
                response=(ServerMsgs._RCheck,(self.username,))

            elif msg==ServerMsgs._StartMotionTrack: # start a motion track job
                jid=self.startMotionTrack(*args)
                response=(ServerMsgs._RStart,(jid,))

            elif msg==ServerMsgs._Stat: # get job status
                jid=args[0]
                jobdir=first(h for p,j,h in self.runningProcs if j==jid)
                if jobdir!=None:
                    #jobdir=os.path.join(jdir,'motiontrack%i'%jid)
                    conf=readBasicConfig(os.path.join(jobdir,trackconfname))
                    numfiles=len(glob.glob(os.path.join(jobdir,'*.dof*')))
                    response=(ServerMsgs._RStat,(conf[JobMetaValues._resultcode],numfiles,conf[JobMetaValues._numtrackfiles],jobdir))
                else:
                    response=(ServerMsgs._RStat,(-1,0,0,''))

            elif msg==ServerMsgs._Kill: # kill a given job
                jid=args[0]
                proc=first(p for p,j,h in self.runningProcs if j==jid)
                if proc!=None:
                    proc.kill()
                response=(ServerMsgs._RKill,(proc!=None,))

            elif msg==ServerMsgs._GetResult: # get the results for a finished job
                jid,isPaths=args
                jdir=first(h for p,j,h in self.runningProcs if j==jid)
                filelist=glob.glob(os.path.join(jdir,'*.dof*'))

                if isPaths: # send the file paths to the results back
                    result=list(filelist)
                else: # send the binary data for the files back
                    result=[]
                    for f in filelist:
                        with open(f) as o:
                            result.append(o.read())

                response=(ServerMsgs._RGetResult,(result,))
            else:
                raise IOError('Unhandled message')

        except Exception as e:
            format_exc=str(traceback.format_exc())
            printFlush(format_exc,stream=sys.stderr)
            response=(ServerMsgs._Except,(e,format_exc))

        wfile.write(pickle.dumps(response))

    def startMotionTrack(self,isPaths,blob,trackfile,maskfile,paramfile,dirname,adaptive,conf,rootdir):
        rootdir=rootdir or self.serverdir

        # calculate the job ID (jid) from the max of the stored jid value and the max numbered motiontrack directory in rootdir
        filejid=self.getJID()
        dirs=glob.glob(os.path.join(rootdir,'motiontrack[0-9]*')) # list the motiontrack dirs in the rootdir (ie. project directory)
        jid=max([0,filejid]+[int(os.path.split(os.path.normpath(d))[1][11:]) for d in dirs])+1

        dirname=dirname or 'motiontrack'
        jobdir=os.path.join(rootdir,'%s_%i'%(dirname,jid))

        for i in range(100): # ensure jobdir doesn't exist but don't loop forever
            if not os.path.exists(jobdir):
                break
            jobdir=os.path.join(rootdir,'%s%i_%i'%(dirname,i,jid))

        os.makedirs(jobdir)

        self.setJID(jid)

        trackname=trackfile
        maskname=maskfile
        paramname=paramfile

        if not isPaths: # if the file data objects not paths, copy the data into local files
            trackname=os.path.join(jobdir,'track.nii')
            with open(trackname,'w') as o:
                o.write(trackfile)

            if maskfile:
                maskname=os.path.join(jobdir,'mask.nii')
                with open(maskname,'w') as o:
                    o.write(maskfile)

            paramname=os.path.join(jobdir,'params.txt')
            with open(paramname,'w') as o:
                o.write(paramfile)

        logfile=os.path.join(jobdir,'output.log')
        args=[self.motiontrackpath,trackname,'-dofout','./','-parin',paramname,'-adaptive',str(adaptive)]

        if maskname:
            args+=['-mask',maskname]

        proc=subprocess.Popen(args,stderr = subprocess.STDOUT, stdout = open(logfile,'w'),cwd=jobdir,close_fds=not isWindows)

        conf.update({
            JobMetaValues._pid         :int(proc.pid),
            JobMetaValues._resultcode  :None,
            JobMetaValues._tracktype   :'motiontrack',
            JobMetaValues._trackfile   :trackfile,
            JobMetaValues._maskfile    :maskfile,
            JobMetaValues._paramfile   :paramfile,
            JobMetaValues._adaptive    :float(adaptive),
            JobMetaValues._startdate   :time.asctime()
        })

        eidolon.storeBasicConfig(os.path.join(jobdir,trackconfname),conf)
        self.runningProcs.append((proc,jid,jobdir))
        return jid


class MotionTrackServerDialog(MotionTrackServerWidget):
    def __init__(self,serverdir,serverport,motiontrackpath):
        MotionTrackServerWidget.__init__(self,serverdir,serverport,motiontrackpath)
        self.setWindowTitle('%s (Port: %i)'%(self.windowTitle(),self.serverport))
        self.show()

    def keyPressEvent(self,e):
        if e.key() == eidolon.Qt.Key_Escape:
            self.close()
        else:
            QtWidgets.QDialog.keyPressEvent(self,e)

    def closeEvent(self,event):
        msg='Closing the server will kill all running jobs, are you sure?'
        reply = QtWidgets.QMessageBox.question(self, 'Quit', msg, QtWidgets.QMessageBox.Yes, QtWidgets.QMessageBox.No)

        if reply == QtWidgets.QMessageBox.Yes:
            self.stopServer()
            event.accept()
        else:
            event.ignore()

    @staticmethod
    def run():
        printFlush('Starting MotionTrackServer on port',sys.argv[2],'using directory',sys.argv[1])
        app = QtWidgets.QApplication(sys.argv)
        mt=MotionTrackServerDialog(*sys.argv[-3:])
        assert mt is not None
        sys.exit(app.exec_())

### Basic plugin implementation using mixin

class BasicIRTKPlugin(eidolon.ImageScenePlugin,IRTKPluginMixin):
    '''Basic implementation of a plugin using the IRTKPluginMixin class.'''
    def __init__(self):
        eidolon.ImageScenePlugin.__init__(self,'IRTK')
        self.project=None

    def init(self,plugid,win,mgr):
        eidolon.ImageScenePlugin.init(self,plugid,win,mgr)
        IRTKPluginMixin.init(self,plugid,win,mgr)
        
        
### Add plugin to environment

eidolon.addPlugin(BasicIRTKPlugin())