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
from struct import unpack,calcsize

HEADER_SIZE=80

keywords=enum('solid','facet normal','outer loop','vertex','endloop','endfacet','endsolid')

class STLPlugin(MeshScenePlugin):
    def __init__(self):
        ScenePlugin.__init__(self,'STL')
        self.objcount=0

    def init(self,plugid,win,mgr):
        MeshScenePlugin.init(self,plugid,win,mgr)
        
        if win:
            win.addMenuItem('Import','STLLoad'+str(plugid),'&STL .stl File',self._openFileDialog)
            
        stlfiles=filter(bool,mgr.conf.get('args','--stl').split(','))
        for f in stlfiles:
            obj=self.loadObject(f)
            self.mgr.addFuncTask(lambda:self.mgr.addSceneObject(obj()))

    def getHelp(self):
        return '\nUsage: --stl=file-path[,file-path]*'
        
    def acceptFile(self,filename):
        return splitPathExt(filename,True)[2].lower()=='.stl'
        
    def getObjFiles(self,obj):
        return [obj.kwargs['filename']]
        
    def copyObjFiles(self,obj,sdir,overwrite=False):
        filename=os.path.join(sdir,os.path.basename(obj.kwargs['filename']))
        copyfileSafe(obj.kwargs['filename'],filename,overwrite)
        obj.kwargs['filename']=filename

    def _openFileDialog(self):
        filename=self.mgr.win.chooseFileDialog('Choose STL filename',filterstr='STL Mesh File (*.stl)')
        if filename!='':
            self.mgr.addFuncTask(lambda:self.mgr.addSceneObject(self.loadObject(filename)),'Importing STL file')

    def loadObject(self,filename,name=None,**kwargs):
        def _readvertex(o,nodes):
            v=o.readline().lower().split()
            assert v[0]==keywords.vertex
            nodes.append(vec3(*map(float,v[1:])))
            
        def _assertline(o,keyword):
            line=o.readline().lower().strip()
            assert line==keyword,'%r != %r'%(line,keyword)
            
        f=Future()
        @taskroutine('Loading STL File')
        def _loadFile(filename,name,task):
            with f:
                name=self.mgr.getUniqueObjName(name or splitPathExt(filename)[1])
                nodes=Vec3Matrix('nodes',0,1)
                normals=RealMatrix('normals',0,3)
                normals.meta(StdProps._topology,'triangles')
                normals.meta(StdProps._spatial,'triangles')
                indices=IndexMatrix('triangles',ElemType._Tri1NL,0,3)
                indices.meta(StdProps._isspatial,'True')
                
                with open(filename,'rb') as o:
                    headcheck=o.read(len(keywords.solid)).lower()
                    if headcheck==keywords.solid: # ascii file
                        name=o.readline().strip()
                        header='%s %s'%(keywords.solid,name)
                        line=o.readline().lower()
                        while line and not line.startswith(keywords.endsolid):
                            assert ('%s %s'%tuple(line.split()[:2]))==keywords.facet_normal
                            normal=map(float,line.split()[2:])
                            normals.append(*normal)
                            _assertline(o,keywords.outer_loop)
                            _readvertex(o,nodes)
                            _readvertex(o,nodes)
                            _readvertex(o,nodes)
                            _assertline(o,keywords.endloop)
                            _assertline(o,keywords.endfacet)
                            line=o.readline().lower()
                    else:
                        header=headcheck+o.read(HEADER_SIZE-len(keywords.solid))
                        numtris=unpack('I',o.read(calcsize('I')))[0]
                        triformat='fff fff fff fff H'
                        trisize=calcsize(triformat)
                        
                        for i in range(numtris):
                            triangle=unpack(triformat,o.read(trisize))
                            normals.append(*triangle[0:3])
                            nodes.append(vec3(*triangle[3:6]))
                            nodes.append(vec3(*triangle[6:9]))
                            nodes.append(vec3(*triangle[9:12]))
                            
                for i in range(0,len(nodes),3):
                    indices.append(i,i+1,i+2)
                    
                f.setObject(MeshSceneObject(name,PyDataSet('STLDS',nodes,[indices],[normals]),self,filename=filename,header=header))
            
        return self.mgr.runTasks(_loadFile(filename,name),f)

    def getScriptCode(self,obj,**kwargs):
        if isinstance(obj,MeshSceneObject):
            configSection=kwargs.get('configSection',False)
            namemap=kwargs.get('namemap',{})
            convertpath=kwargs['convertPath']
            script=''
            args={'varname':namemap[obj],'objname':obj.name}
            
            if 'filename' in obj.kwargs:
                args['filename']=convertpath(obj.kwargs['filename'])

            if not configSection and 'filename' in args:
                script='%(varname)s=STL.loadObject(%(filename)s,%(objname)r)\n'
            
            return setStrIndent(script % args).strip()+'\n'
        else:
            return MeshScenePlugin.getScriptCode(self,obj,**kwargs)     
            
        
addPlugin(STLPlugin())