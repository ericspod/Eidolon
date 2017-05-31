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

from eidolon import *

import ast
import os
import numpy as np

addLibraryFile('x4df-0.1.0-py2-none-any')

import x4df
from x4df import readFile, writeFile, idTransform, validFieldTypes, ASCII, BASE64, BASE64_GZ, BINARY, BINARY_GZ

ConfigArgs=enum(
    ('filename','Name of .x4df file the object is stored in'),
    ('filenames','Names of array files, may be [] or not present'),
    ('loadorder','Which mesh/image the object is loaded from in the original file'),
    ('source','Source object the data for this object was loaded from')
)


def array2MatrixForm(arr,dtype):
    '''Return the equivalent of `arr' with a 2D shape and with the given type.'''
    shape=arr.shape
    if len(shape)==1:
        arr=arr.reshape((shape[0],1))
    elif len(shape)>2:
        arr=arr.reshape((sum(shape)/shape[1],shape[1]))
    else:
        arr=arr

    return arr.astype(dtype)


@timing
def convertMesh(obj,arrayformat=ASCII,filenamePrefix=None):
    '''
    Convert the MeshSceneObject `obj' into a x4df structure. The arrays are all formatted the same using `arrayformat'
    and are stored in files whose names begin with `filenamePrefix' if this is given (or if the format is binary in
    which case the name of `obj' is the prefix if this is not given), otherwise they are stored in the XML document.
    The return value is a single x4df object containing a single mesh.
    '''
    ts=obj.getTimestepList()
    if arrayformat in (BINARY, BINARY_GZ):
        filenamePrefix=filenamePrefix or obj.getName()

    x4=x4df.x4df([],[],[],[])
    m=x4df.mesh(obj.getName(),None,[],[],[],[])
    x4.meshes.append(m)

    # nodes first
    for i,ds in enumerate(obj.datasets):
        nodesmat=np.asarray(ds.getNodes())
        shape=x4df.toNumString(np.asarray(nodesmat.shape),int)
        step=ts[i] if len(ts)>1 else None
        src='nodes_%i'%i
        filename='%s_%s.dat'%(filenamePrefix,src) if filenamePrefix else None

        nodes_=x4df.nodes(src,None,step,[])
        arr=x4df.array(src,shape,'CR','f8',arrayformat,None,filename,nodesmat)

        m.nodes.append(nodes_)
        x4.arrays.append(arr)

    # spatial topologies only for now?
    for ind in obj.datasets[0].enumIndexSets():
        if isSpatialIndex(ind):
            indmat=np.asarray(ind)
            shape=' '.join(map(str,indmat.shape))
            filename='%s_%s.dat'%(filenamePrefix,ind.getName()) if filenamePrefix else None

            topo=x4df.topology(ind.getName(),ind.getName(),ind.getType(),ind.meta(StdProps._spatial),[])
            arr=x4df.array(ind.getName(),shape,None,'u4',arrayformat,None,filename,indmat)
            m.topologies.append(topo)
            x4.arrays.append(arr)

    # fields
    for i,ds in enumerate(obj.datasets):
        for df in ds.enumDataFields():
            isTimeCopy=df.meta(StdProps._timecopy).lower()=='true'
            dfmat=np.asarray(df)
            shape=x4df.toNumString(np.asarray(dfmat.shape),int)
            topo=df.meta(StdProps._topology) or None
            spatial=df.meta(StdProps._spatial) or None
            ftype=validFieldTypes[1 if df.meta(StdProps._elemdata).lower()=='true' else 0]
            step=ts[i] if len(ts)>1 else None
            src=df.getName()

            if not isTimeCopy:
                src='%s_%i'%(src,i)

            f=x4df.field(df.getName(),src,step,topo,spatial,ftype,[])
            m.fields.append(f)

            if not isTimeCopy or i==0:
                filename='%s_%s.dat'%(filenamePrefix,src) if filenamePrefix else None
                arr=x4df.array(src,shape,'CR','f8',arrayformat,None,filename,dfmat)
                x4.arrays.append(arr)

    return x4


@timing
def convertImage(obj,arrayformat=ASCII,dataFormat='f4',filenamePrefix=None):
    if len(obj.getOrientMap())>1:
        raise NotImplementedError('Cannot yet convert image objects which are not single 2D planes or 3D volumes')

    tmpplugin=ImageScenePlugin('tmp')
    start,step=obj.getTimestepScheme()
    tscheme=(start,step) if start!=0 or step!=0 else None

    if arrayformat in  (BINARY, BINARY_GZ):
        filenamePrefix=filenamePrefix or obj.getName()

    filename='%s.dat'%filenamePrefix if filenamePrefix else None

    imgarrmap=tmpplugin.getImageObjectArray(obj)
    imgarr=imgarrmap['dat']
    pos=imgarrmap['pos']
    shape=imgarrmap['shape']
    spacing=imgarrmap['spacing']*vec3(shape[1],shape[0],shape[2])
    rot=imgarrmap['rot']

    trans=x4df.transform(np.asarray(list(pos)),np.asarray(rot.toMatrix())[:3,:3].flatten(),np.asarray(list(spacing)))

    x4=x4df.x4df([],[],[],[])
    im=x4df.image(obj.getName(),tscheme,trans,[],[])
    x4.images.append(im)

    imd=x4df.imagedata('image',None,None,[])
    im.imagedata.append(imd)

    x4.arrays.append(x4df.array('image',' '.join(map(str,imgarr.shape)),None,dataFormat,arrayformat,None,filename,imgarr))

    return x4


def importMeshes(x4):
    arrs={a.name:a for a in x4.arrays}
    results=[]

    for m in x4.meshes:
        name, ts, mnodes, topos, dfs,_=m
        topomats=[]
        dss=[]
        timesteps=[0]
        filenames=[]
        dfmap=dict()

        for df in dfs:
            dfmap.setdefault(df.name,[]).append(df)

        # sort fields by timestep
        for dfn in dfmap:
            dfmap[dfn]=sorted(dfmap[dfn],key=lambda i:(i.timestep or 0))

        # determine timestep from timescheme value, node timestep values, or field timestep values
        if len(mnodes)>1 or ts or len(dfs)>1:
            if ts: # convert timescheme to timestep list
                timesteps=frange(ts[0],ts[1]*len(mnodes),ts[1])
            elif len(mnodes)>1:
                timesteps=[n.timestep or i for i,n in enumerate(mnodes)]
            else:
                timedf=first(dfs for dfs in dfmap.values() if len(dfs)>1)
                if timedf:
                    timesteps=[df.timestep or i for i,df in enumerate(timedf)]

        assert len(timesteps)==len(mnodes) or len(timesteps)==len(first(dfmap.values()))

        # read topologies in first, these get copied between timesteps
        for t in topos:
            tname, tsrc, et, spatial,_=t
            arr=array2MatrixForm(arrs[tsrc].data,np.uint32)
            tmat=IndexMatrix(tname,et or '',*arr.shape)
            filenames.append(arrs[tsrc].filename)

            if spatial:
                tmat.meta(StdProps._spatial,spatial)
                tmat.meta(StdProps._isspatial,'False')
            else:
                tmat.meta(StdProps._isspatial,'True')

            np.asarray(tmat)[:,:]=arr
            topomats.append(tmat)

        # read each timestep, first copying the nodes then the field for the timestep or cloning static fields
        for i in range(len(timesteps)):
            fields=[]
            arr=arrs[mnodes[i].src].data
            initnodes=arrs.get(mnodes[i].initialnodes,0) # get initial nodes or default 0
            filenames.append(arrs[mnodes[i].src].filename)

            nmat=Vec3Matrix('nodes%i'%i, arr.shape[0])
            np.asarray(nmat)[:,:]=array2MatrixForm(arr+initnodes,np.double)

            # read in each field, there will be a separate entry for this timestep or a single entry that is copied for each timestep
            for dfs in dfmap.values():
                findex=0 if len(dfs)==1 else i # choose the first field value if this field is static, every timestep gets a copy
                fname, src, _, ftopo, fspatial, fieldtype, _=dfs[findex]
                arr=array2MatrixForm(arrs[src].data,np.double)
                filenames.append(arrs[src].filename)

                fmat=RealMatrix(fname,*arr.shape)
                fmat.meta(StdProps._topology,ftopo)
                fmat.meta(StdProps._spatial,fspatial)
                fmat.meta(StdProps._elemdata,str(fieldtype==validFieldTypes[0]))
                fmat.meta(StdProps._timecopy,str(len(dfs)>1))

                np.asarray(fmat)[:,:]=arr
                fields.append(fmat)

            dss.append(PyDataSet('%s%i'%(name,i),nmat,topomats,fields))

        obj=MeshSceneObject(name,dss,filenames=filter(bool,filenames))

        # set timestep list if needed
        if len(timesteps)>1:
            obj.setTimestepList(map(ast.literal_eval,timesteps))

        results.append(obj)

    return results


def importImages(x4):
    arrs={a.name:a for a in x4.arrays}
    results=[]
    tmpplugin=ImageScenePlugin('tmp')

    for im in x4.images:
        name, timescheme, trans, imagedata,_=im
        images=[]
        filenames=[]
        tstart,tstep=timescheme or (0,0)
        trans=trans or idTransform

        for i,imgdat in enumerate(imagedata):
            src, timestep, imgtrans,_=imgdat
            arr=arrs[src].data
            imgtrans=imgtrans or trans

            filenames.append(arrs[src].filename)

            if timestep is None:
                offset,interval=tstart,tstep
            else:
                offset,interval=tstart+i*tstep,0

            pos=vec3(*imgtrans.position)
            rot=rotator(*imgtrans.rmatrix.flatten())
            spacing=vec3(*imgtrans.scale)*vec3(arr.shape[1], arr.shape[0], arr.shape[2] if len(arr.shape)>2 else 0).inv()

            obj=tmpplugin.createObjectFromArray('tmp',arr,interval,offset,pos,rot,spacing)
            images+=obj.images

        results.append(ImageSceneObject(name,None,images,filenames=filter(bool,filenames)))

    return results


class X4DFPlugin(CombinedScenePlugin):
    def __init__(self):
        CombinedScenePlugin.__init__(self,'X4DF')
        self.objcount=0

    def init(self,plugid,win,mgr):
        CombinedScenePlugin.init(self,plugid,win,mgr)

        if win:
            win.addMenuItem('Import','X4DFLoad'+str(plugid),'&X4DF File',self._openFileDialog)
            win.addMenuItem('Export','X4DFSave'+str(plugid),'&X4DF File',self._saveFileDialog)

    def acceptFile(self,filename):
        return splitPathExt(filename)[2].lower() == '.x4df'

    def checkFileOverwrite(self,obj,dirpath,name=None):
        newname=name or obj.getName()
        oldfiles=self.getObjFiles(obj)
        oldbasename=splitPathExt(oldfiles[0])[1] # old basename of the x4df file
        newfiles=[os.path.join(dirpath,os.path.basename(f).replace(oldbasename,newname)) for f in oldfiles]

        return filter(os.path.exists,newfiles)

    def getObjFiles(self,obj):
        return [obj.kwargs['filename']]+obj.kwargs['filenames']

    def copyObjFiles(self,obj,sdir,overwrite=False):
        overfiles=self.checkFileOverwrite(obj,sdir)
        if not overwrite and overfiles:
            raise IOError('Cannot overwrite files '+', '.join(overfiles))

        newfiles=[]

        for f in self.getObjFiles(obj):
            newfile=os.path.join(sdir,os.path.basename(f))
            copyfileSafe(f,newfile,overwrite)
            newfiles.append(newfile)

        obj.kwargs['filename']=newfiles[0]
        obj.kwargs['filenames']=newfiles[1:]

    def renameObjFiles(self,obj,oldname,overwrite=False):
        if obj.getName()==oldname:
            return

        newname=obj.getName()
        newfiles=[]
        oldbasename=splitPathExt(obj.kwargs['filename'])[1]

        overfiles=self.checkFileOverwrite(obj,'',newname)
        if not overwrite and overfiles:
            raise IOError('Cannot overwrite files '+', '.join(overfiles))

        for f in self.getObjFiles(obj):
            newbasename=splitPathExt(f)[1].replace(oldbasename,newname)
            newfiles.append(renameFile(f,newbasename,overwriteFile=overwrite))

        obj.kwargs['filename']=newfiles[0]
        obj.kwargs['filenames']=newfiles[1:]

    @taskmethod('Loading X4DF Object')
    def loadObject(self,filename,name=None,task=None,**kwargs):
        printFlush(task)
        x4=timing(readFile)(filename)
        objs=timing(importMeshes)(x4)+timing(importImages)(x4)
        #basepath=os.path.dirname(filename)

        # free array data but keep the rest
        for a in x4.arrays:
            a.data=None

        # set config data
        for i,o in enumerate(objs):
            o.plugin=self
            o.kwargs[ConfigArgs._filename]=filename
            o.kwargs[ConfigArgs._loadorder]=i
            o.kwargs[ConfigArgs._source]=x4

        return objs

    @taskmethod('Saving X4DF Object')
    def saveObject(self,obj,path,overwrite=False,setFilenames=False,task=None,arrayFormat=BASE64_GZ,dataFormat='f4',separateFiles=False,**kwargs):
        path=ensureExt(path,'.x4df')
        fileprefix=os.path.splitext(path) if separateFiles else None

        if not overwrite and os.path.exists(path):
            raise IOError('Cannot overwrite file %r'%path)

        if isinstance(obj,MeshSceneObject):
            x4=convertMesh(obj,arrayFormat,fileprefix)
        else:
            x4=convertImage(obj,arrayFormat,dataFormat,fileprefix)

        timing(writeFile)(x4,path)

        # free array data but keep the rest
        for a in x4.arrays:
            a.data=None

        if setFilenames:
            obj.plugin=self
            obj.kwargs[ConfigArgs._filename]=path
            obj.kwargs[ConfigArgs._filenames]=[a.filename for a in x4.arrays if a.filename]
            obj.kwargs[ConfigArgs._loadorder]=0
            obj.kwargs[ConfigArgs._source]=x4

    def _openFileDialog(self):
        filename=self.mgr.win.chooseFileDialog('Choose X4DF filename',filterstr='VTK Files (*.x4df)')
        if filename:
            self.mgr.addFuncTask(lambda:map(self.mgr.addSceneObject,self.loadObject(filename)),'Importing X4DF file')

    def _saveFileDialog(self):
        obj=self.win.getSelectedObject()
        if isinstance(obj,SceneObjectRepr):
            obj=obj.parent

        filename=self.mgr.win.chooseFileDialog('Choose X4DF filename',filterstr='X4DF Files (*.x4df)',isOpen=False)
        if filename!='':
            f=self.saveObject(obj,filename,True)
            self.mgr.checkFutureResult(f)

    def getScriptCode(self,obj,**kwargs):
        if isinstance(obj,MeshSceneObject):
            configSection=kwargs.get('configSection',False)
            namemap=kwargs.get('namemap',{})
            convertpath=kwargs['convertPath']
            script=''
            args={'varname':namemap[obj], 'objname':obj.name,'loadorder':obj.source['loadorder']}

            if not configSection:
                args['filename']=convertpath(obj.kwargs['filename'])
                script+='%(varname)s=X4DF.loadObject(%(filename)s,%(objname)r)[%(loadorder)]'

            return setStrIndent(script % args).strip()+'\n'
        else:
            return MeshScenePlugin.getScriptCode(self,obj,**kwargs)


addPlugin(X4DFPlugin())
