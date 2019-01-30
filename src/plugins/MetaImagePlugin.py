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


import eidolon
from eidolon import (
    enum, ImageScenePlugin, taskroutine, ensureExt, copyfileSafe, renameFile, splitPathExt, 
    Future, vec3, rotator, ImageSceneObject,ImageSceneObjectRepr
)

import zlib
import os
import math
import numpy as np


MetaImageTypes=enum(
    ('MET_FLOAT','f'),  # C equivalent: float
    ('MET_DOUBLE','d'), # C equivalent: double
    ('MET_CHAR','b'),   # C equivalent: char or int8_t
    ('MET_UCHAR','B'),  # C equivalent: unsigned char or uint8_t
    ('MET_SHORT','h'),  # C equivalent: short or int16_t
    ('MET_USHORT','H'), # C equivalent: unsigned short or uint16_t
    ('MET_INT','i'),    # C equivalent: int or int32_t
    ('MET_UINT','I'),   # C equivalent: unsigned int or uint32_t
    ('MET_LONG','l'),   # C equivalent: long long or int64_t
    ('MET_ULONG','L'),  # C equivalent: unsigned long long or uint64_t
    desc='Maps the MetaImage pixel type to the equivalent Numpy datatype'
)


class MetaImagePlugin(ImageScenePlugin):
    # this defines the header ordering which appears to be sacred to some software
    HeaderNames=(
        'ObjectType','NDims','BinaryData','BinaryDataByteOrderMSB','CompressedData','TransformMatrix',
        'Offset','CenterOfRotation','ElementSpacing','DimSize','AnatomicalOrientation','ElementType','ElementDataFile'
    )

    def __init__(self):
        ImageScenePlugin.__init__(self,'MetaImg')

    def init(self,plugid,win,mgr):
        ImageScenePlugin.init(self,plugid,win,mgr)
        if win:
            win.addMenuItem('Import','MetaImgLoad'+str(plugid),'&MetaImage File',self._openFileDialog)
            win.addMenuItem('Export','MetaImgExport'+str(plugid),'&MetaImage File',self._exportMenuItem)

        # read command line argument, loading files as requested, note these tasks are queued at module load time
        if mgr.conf.hasValue('args','--metaimg'):
            metaload=mgr.conf.get('args','--metaimg').split(',')
            filereprs=[]
            for m in metaload:
                if m in eidolon.ReprType and len(filereprs)>0:
                    filereprs[-1][1]=m
                else:
                    filereprs.append([m,None])

            @taskroutine('Loading MetaImage File(s)')
            def _loadTask(filereprs,task=None):
                for m,reprtype in filereprs:
                    obj=self.loadObject(m)
                    self.mgr.addSceneObject(obj)

                    if reprtype!=None:
                        rep=obj.createRepr(reprtype)
                        self.mgr.addSceneObjectRepr(rep)
                        self.mgr.setCameraSeeAll()

            self.mgr.runTasks([_loadTask(filereprs)])

    def getHelp(self):
        return '\nUsage: --metaimg=header-file-path[,representation-type][,...]'

    def getObjFiles(self,obj):
        filename=obj.source['filename']
        _,ext=os.path.splitext(filename)
        if ext.lower()=='.mha':
            return [filename]
        else:
            return [filename,ensureExt(filename,'.raw',True)]

    def copyObjFiles(self,obj,sdir,overwrite=False):
        files=self.getObjFiles(obj)
        filename=os.path.join(sdir,os.path.basename(files[0]))
        
        copyfileSafe(files[0],filename,overwrite)
        obj.kwargs['filename']=filename
        
        if len(files)==2:
            copyfileSafe(files[1],os.path.join(sdir,os.path.basename(files[1])),overwrite)

    def renameObjFiles(self,obj,oldname,overwrite=False):
        assert isinstance(obj,eidolon.SceneObject) and obj.plugin==self
        oldpath=obj.source['filename']
        rawfile=ensureExt(oldpath,'.raw',True)
        if os.path.isfile(rawfile):
            renameFile(rawfile,obj.getName(),overwriteFile=overwrite)

        obj.source['filename']=renameFile(oldpath,obj.getName(),overwriteFile=overwrite)
        
    def acceptFile(self,filename):
        return splitPathExt(filename,True)[2].lower() in ('.mha','.mhd')

    def loadImage(self,filename,name=None,**kwargs):
        '''Deprecated, for compatibility only.'''
        return self.loadObject(filename,name)

    def loadObject(self,filename,name=None,**kwargs):
        '''
        Loads a MetaImage image object from the header file `filename', which may contain the image data or refer to
        a raw file which is then read. If `name' is None then a name for the returned ImageSceneObject is chosen from
        `filename', otherwise `name' is used.
        '''
        def _isBinaryLine(line):
            '''A line is binary data if it contains successive null characters or any character >=127 (not ASCII).'''
            return '\00\00' in line or any(ord(l)>=127 for l in line)

        f=Future()

        @taskroutine('Loading MetaImage File')
        def _loadFile(filename,name,task):
            with f:
                filename=Future.get(filename)
                basename=name or os.path.basename(filename).split('.')[0]
                name=eidolon.uniqueStr(basename,[o.getName() for o in self.mgr.enumSceneObjects()]) # choose object name based on file name
                hdr={}
                raw=''

                # read each line of data, lines that don't have 2 nulls are header, all others data
                with open(filename,'r') as o:
                    line=o.readline()
                    while line!='' and not _isBinaryLine(line): # lines that don't have 2 nulls are header lines
                        k,v=line.split('=')
                        hdr[k.strip()]=v.strip()
                        line=o.readline()

                    if line!='': # store the rest as the data components
                        raw=line+o.read()

                elemtype=hdr['ElementType']
                dim=int(hdr['NDims']) # 3 for static image, 4 for time-dependent
                dimsize=list(map(int,hdr['DimSize'].split())) # XYZ or XYZT if dim==4
                offset=list(map(float,hdr['Offset'].split()))
                trans=list(map(float,hdr['TransformMatrix'].split()))
                espacing=list(map(float,hdr['ElementSpacing'].split()))
                datfile=hdr['ElementDataFile']
                toffset=(0 if len(offset)==3 else offset[-1])*1000.0
                interval=(1.0 if len(espacing)==3 else espacing[-1])*1000.0
                position=vec3(*offset[:3])
                spacing=vec3(*espacing[:3])

                assert elemtype in MetaImageTypes, '%r not recognized'%elemtype
                assert dim in (3,4),'dim is %r, should be 3 or 4'%len(dimsize)
                assert len(dimsize)==dim,'%i!=%i'%(len(dimsize),dim)
                assert len(espacing)==dim,'%i!=%i'%(len(espacing),dim)
                assert len(trans) in (9,16),'%i!=9 or 16'%len(trans)
                assert datfile=='LOCAL' or raw==''

                if len(trans)==16:
                    a,b,c,_,d,e,g,_,c1,c2,c3,_=trans[:12]
                else:
                    a,b,c,d,e,g,c1,c2,c3=trans[:9]

                right=vec3(a,b,c)
                down=vec3(d,e,g)
                rot=rotator(right,down,vec3.X(),-vec3.Y())
                cross=vec3(c1,c2,c3)
                
                # need to infer stack direction from the cross product, invert Z pixel spacing direction if needed because reasons
                if right.cross(down).angleTo(cross)<math.pi/10: 
                    spacing*=vec3(1,1,-1)
                    
                if datfile=='LOCAL':
                    datfile=filename
                else:
                    datfile=os.path.join(os.path.split(filename)[0],datfile)
                    with open(datfile,'rb') as o:
                        raw=o.read()

                # decompress image data
                if raw and hdr.get('CompressedData','').lower()=='true':
                    comsize=int(hdr.get('CompressedDataSize',0))
                    assert comsize in (0,len(raw)),'Raw data length (%i) does not match specified length (%i)'%(len(raw),comsize)
                    raw=zlib.decompress(raw)

                hdr['datfile']=datfile
                hdr['filename']=filename

                dat=np.ndarray(dimsize,dtype=np.dtype(MetaImageTypes[elemtype]),buffer=raw.encode(),order='F')
                #dat=eidolon.transposeRowsColsNP(dat) # transpose from row-column to column-row

                obj=self.createObjectFromArray(name,dat,interval,toffset,position,rot,spacing,task=task)
                obj.source=hdr
                f.setObject(obj)

        return self.mgr.runTasks([_loadFile(filename,name)],f)

    def saveImage(self,filename,obj,**kwargs):
        '''Deprecated, for compatibility only.'''
        return self.saveObject(obj,filename,**kwargs)
        
    def saveObject(self,obj,path,overwrite=False,setFilenames=False,**kwargs):
        '''
        Saves the given ImageSceneObject `obj' to MetaImage file(s) prefixed with `path'. If `path' doesn't
        end with .mhd or .mha, then the keyword argument `isOneFile' is used to determine whether to save as one file or
        header/raw pair. In this case if `isOneFile' is True then header is stored to `path'+".mhd" and the data
        in `path'+".raw". However, if either extension is given in `path', these are used to determine whether
        to write to one file or two if `isOneFile' isn't present. If a MetaImage type is supplied in the keyword argument
        `datatype' then the image data will be stored in that format, otherwise MET_SHORT is used. Any other keyword
        arguments are added to the end of the header, or override those values named in `HeaderNames'.
        '''
        f=Future()

        @taskroutine('Saving MetaImage File')
        def _saveFile(path,obj,kwargs,task):
            with f:
                filenamepart,ext=os.path.splitext(path)
                ext=ext.lower()
                isOneFile=kwargs.pop('isOneFile',ext=='.mha')
                datfile='LOCAL'

                if ext not in ('.mhd','.mha'):
                    if isOneFile:
                        path+='.mha'
                    else:
                        datfile=path+'.raw'
                        path+='.mhd'
                elif not isOneFile:
                    datfile=filenamepart+'.raw'

                datatype=kwargs.pop('datatype',MetaImageTypes._MET_SHORT) # choose output datatype, MET_SHORT is default

                # convert the image into a 2D/3D/4D matrix and pull out the header information
                mat=self.getImageObjectArray(obj,MetaImageTypes[datatype])
                dat=mat['array']
                pos=obj.getTransform()*vec3.Z() # choose the top corner as the origin instead of mat['pos'] for compatibility with other programs
                spacing=[i or 1 for i in mat['spacing']] # all values of spacing must be non-zero
                rot=mat['rot']
                toffset=mat['toffset']
                interval=mat['interval']
                cols,rows,depth,numsteps=dat.shape
                dims=4 if obj.isTimeDependent else 3

                xdir=rot*vec3.X()
                ydir=rot*-vec3.Y()
                zdir=xdir.cross(ydir)
                
                if dims==4:
                    transmat=list(xdir)+[0]+list(ydir)+[0]+list(zdir)+[0,0,0,0,1]
                else:
                    transmat=list(xdir)+list(ydir)+list(zdir)

                hdr={
                    'ObjectType'             : 'Image',
                    'NDims'                  : dims,
                    'ElementType'            : datatype,
                    'DimSize'                : [cols,rows,depth]+([numsteps] if dims==4 else []),
                    'ElementSpacing'         : list(spacing)+([interval/1000.0] if dims==4 else []),
                    'Offset'                 : list(pos)+([toffset/1000.0] if dims==4 else []),
                    'ElementDataFile'        : os.path.basename(datfile),
                    'TransformMatrix'        : transmat,
                    'AnatomicalOrientation'  : '????',
                    'BinaryData'             : 'True',
                    'BinaryDataByteOrderMSB' : 'False',
                    'CenterOfRotation'       : [0,0,0,0],
                    'CompressedData'         : 'False'
                }

                hdrnames=list(self.HeaderNames)+[k for k in kwargs if k not in self.HeaderNames]
                hdr.update(kwargs)
                
                #dat=np.transpose(dat,(1,0,2,3)[:len(dat.shape)]) # transpose rows and columns
                
                dat=dat[:,:,::-1,...] # since the top corner is the origin, invert the Z axis in the matrix
                dat=np.squeeze(dat)

                with open(path,'w') as o:
                    for k in hdrnames:
                        v=hdr[k]
                        if isinstance(v,str) or not eidolon.isIterable(v):
                            sv=str(v)
                        else:
                            sv=' '.join(map(str,hdr[k]))
                        o.write('%s = %s\n'%(k,sv))

#                    if isOneFile:
#                        o.write(dat.tostring(order='F'))
#
#                if not isOneFile:
#                    with open(datfile,'wb') as o:
#                        o.write(dat.tostring(order='F'))
                        
                if isOneFile:
                    datfile=path
                    
                with open(datfile,'ab' if isOneFile else 'wb') as o:
                    o.write(dat.tostring(order='F'))

                f.setObject((hdr,dat))

        return self.mgr.runTasks([_saveFile(path,obj,kwargs)],f)

    def _openFileDialog(self):
        filename=self.mgr.win.chooseFileDialog('Choose MetaImage Header filename',filterstr='Header Files (*.mhd *.mha)')
        if filename!='':
            self.mgr.addFuncTask(lambda:self.mgr.addSceneObject(self.loadObject(filename)),'Importing MetaImage file')

    def _exportMenuItem(self):
        obj=self.win.getSelectedObject()
        if not isinstance(obj,(ImageSceneObject,ImageSceneObjectRepr)):
            self.mgr.showMsg('Error: Must select image data object to export','MetaImage Export')
        else:
            if isinstance(obj,ImageSceneObjectRepr):
                obj=obj.parent

            filename=self.mgr.win.chooseFileDialog('Choose MetaImage Header filename',filterstr='Header Files (*.mhd *.mha)',isOpen=False)
            if filename!='':
                f=self.saveImage(filename,obj)
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

            script+='%(varname)s = MetaImg.loadObject(%(filename)s,%(objname)r)\n'

        elif isinstance(obj,ImageSceneObjectRepr):
            args={
                'varname':varname,
                'pname':namemap[obj.parent],
                'reprtype':obj.reprtype,
                'matname':namemap.get(obj.getMaterialName(),'BaseImage')
            }

            if configSection:
                script= ImageScenePlugin.getScriptCode(self,obj,setMaterial=False,**kwargs)
            else:
                script= "%(varname)s=%(pname)s.createRepr(ReprType._%(reprtype)s,imgmat=%(matname)s)\n"

        return eidolon.setStrIndent(script % args).strip()+'\n'


eidolon.addPlugin(MetaImagePlugin())