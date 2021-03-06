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
        QtWidgets, MeshSceneObject,MeshScenePlugin, ElemType, ReprType,PyDataSet, Vec3Matrix, BoundBox, transform,
        chooseProcCount, delegatedmethod, taskmethod, first, concurrent
)

from ..ui import Ui_DeformObjProp

autoUpdateDelay=2.0

gridType=ElemType.Hex1PCR

deformRepr='deform'
specialRepr='specialRepr'
tempDS='tempDS'
specialReprs=eidolon.enum('handlelines','deformedmesh')
    

@concurrent
def calculateNodeXisRange(process,nodes,trans,xis,minv,diff):
    for n in process.prange():
        xi=((trans*nodes[n])-minv)/diff
        xis[n]=tuple(xi)


def calculateNodeXis(nodes,trans,boundbox=None,task=None):
    boundbox=boundbox or BoundBox(nodes)
    minv=boundbox.minv
    maxv=boundbox.maxv
    diff=maxv-minv
    
    assert not diff.isZero()
    
    proccount=chooseProcCount(len(nodes),0,1000)
    nodes.setShared(proccount!=1)
    xis=eidolon.RealMatrix('xis',len(nodes),3,proccount!=1)
    
    calculateNodeXisRange(len(nodes),proccount,task,nodes,trans,xis,minv,diff)
        
    return xis


@concurrent
def calculateNodeCoeffsRange(process,xis,wpts,hpts,dpts):
    coeffs=[]
    
    for n in process.prange():
        x,y,z=xis[n]
        ncoeffs=gridType.basis(x,y,z,wpts,hpts,dpts,limits=[(0,0)]*3)
        coeffmap={i:v for i,v in enumerate(ncoeffs) if eidolon.epsilonZero(v)!=0}
        coeffs.append(coeffmap)
        
    return coeffs


def calculateNodeCoeffs(xis,wpts,hpts,dpts,task=None):
    proccount=chooseProcCount(len(xis),0,1000)
    if proccount!=1:
        eidolon.shareMatrices(xis)
    
    result=calculateNodeCoeffsRange(xis.n(),proccount,task,xis,wpts,hpts,dpts)
    
    eidolon.checkResultMap(result)
    
    return eidolon.sumResultMap(result)


@concurrent
def applyCoeffsRange(process,coeffs,ctrlpts,outnodes):
    ctrlpts=ctrlpts[:,0]
    
    for n in process.prange():
        ncoeff=[0]*len(ctrlpts)
        for i,v in coeffs[n].items():
            ncoeff[i]=v
            
        outnodes[n]=ElemType.Point.applyCoeffs(ctrlpts,ncoeff)
        

def applyCoeffs(coeffs,ctrlpts,outnodes,task=None):
    proccount=chooseProcCount(len(coeffs),0,1000)
    
    if not outnodes:
        outnodes=eidolon.Vec3Matrix('nodes',len(coeffs),1,proccount!=1)
    elif proccount!=1:
        eidolon.shareMatrices(outnodes,ctrlpts)
        
    applyCoeffsRange(outnodes.n(),proccount,task,coeffs,ctrlpts,outnodes)
    
    return outnodes
    

def generateControlBox(bbmin,bbmax,dimx,dimy,dimz):
    if bbmax<=bbmin:
        raise ValueError('Invalid bound box: %r -> %r'%(bbmin,bbmax))
        
    if dimx<=2 or dimy<=2 or dimz<=2:
        raise ValueError('Invalid dimensions, must be >2 (%r, %r, %r)'%(dimx,dimy,dimz))
    
    nodes,hexes=eidolon.generateHexBox(dimx-2,dimy-2,dimz-2) # generate a hex grid
    _,lineinds=eidolon.generateLineBox((bbmin,bbmax)) # get indices for a line box
    
    bbdiff=bbmax-bbmin
    nodes=[n*bbdiff+bbmin for n in nodes]
    lines=set()
    
    # convert hexes into line indices joining the edges
    for h in hexes:
        for i,j in lineinds:
            hi,hj=h[i],h[j]
            lines.add((min(hi,hj),max(hi,hj)))
            
    return nodes,sorted(lines)
    

class DeformPropertyWidget(QtWidgets.QWidget,Ui_DeformObjProp):
    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self,parent)
        self.setupUi(self)
        
    def getGridSize(self):
        return self.xgridBox.value(),self.ygridBox.value(),self.zgridBox.value()
    
    def setGridSize(self,x,y,z):
        self.xgridBox.setValue(x)
        self.ygridBox.setValue(y)
        self.zgridBox.setValue(z)
    
    def getMeshType(self):
        return ReprType._line if self.lineButton.isChecked() else ReprType._volume
    

class DeformSceneObject(MeshSceneObject):
    def __init__(self,name,plugin=None,**kwargs):
        self.ctrls=Vec3Matrix('ctrl',1)
        self.ctrldims=(1,1,1) # XYZ dimensions of the control point grid
        
        self.lineinds=eidolon.IndexMatrix('lines',ElemType._Line1NL,1,2)
        self.sourceObj=None
        self.sourceCoeffs=None
        self.sourceXis=None
        
        self.deformReprType=ReprType._volume
        
        dataset=PyDataSet('ctrls',self.ctrls,[self.lineinds])
        
        MeshSceneObject.__init__(self,name,dataset,plugin)
    
    def setControlPoint(self,index,position):
        '''
        Set the control point number `index' to the relative coordinate `position'. These coordinates are relative to the
        control point representation position, thus that object's transform must be applied to get world coordinates.
        '''
        oldpos=self.ctrls[index]
        self.ctrls[index]=position
        
        ctrlrep=self.getCtrlPointRepr()
        if ctrlrep:
            for i in range(ctrlrep.nodes.n()):
                n=ctrlrep.nodes[i][0]
                if n==oldpos:
                    ctrlrep.nodes[i,0]=position
    
    def setControlBox(self,bbmin,bbmax,dimx,dimy,dimz):
        '''
        Set a new control point box of nodes on an axis-aligned grid in the bounding region (bbmin,bbmax) with dimensions
        (dimx,dimy,dimz). This will create a set of control nodes dimx*dimy*dimz in size in self.ctrls and set 
        self.lineinds to contain a line topology representing the control point grid.
        '''
        nodes,lines=generateControlBox(bbmin,bbmax,dimx,dimy,dimz)
        
        assert len(nodes)==(dimx*dimy*dimz),'%i %i %i %i'%(len(nodes),dimx,dimy,dimz)
        
        self.ctrldims=(dimx,dimy,dimz)
        
        self.ctrls.setShared(False)
        self.ctrls.setN(len(nodes))
        self.ctrls[:]=nodes
        
        self.lineinds.setShared(False)
        self.lineinds.setN(len(lines))
        self.lineinds[:]=lines
        
    def getCtrlPointRepr(self):
        return first(r for r in self.reprs if r.kwargs.get('specialRepr','')==specialReprs.handlelines)
    

class DeformPlugin(MeshScenePlugin):
    def __init__(self):
        MeshScenePlugin.__init__(self,'Deform')
        
        eidolon.delayedMethodWeak(self,'_delayUpdateRepr',autoUpdateDelay)

    def init(self,plugid,win,mgr):
        MeshScenePlugin.init(self,plugid,win,mgr)
        
        def _createDef():
            self.mgr.addSceneObject(self.createDeformObject())
        
        win.addMenuItem('Create','NewDeform'+str(plugid),'&Deformation Object',_createDef)
        
    def createDeformObject(self,name='deform'):
        return DeformSceneObject(name,self)
        
    def getReprTypes(self,obj):
        return [ReprType._line]
        
    @taskmethod('Creating Representation')
    def createRepr(self,obj,reprtype,refine=0,drawInternal=False,externalOnly=True,matname='Default',task=None,**kwargs):
        if obj.sourceObj is None or obj.ctrls.n()==1:
            raise ValueError('Deform object must have source and nodes set before creating representations')
            
        # create the deformed mesh representation
        if reprtype==deformRepr:# and not any(r.kwargs.get(specialRepr,'')==specialReprs.deformedmesh for r in obj.reprs):
            # create a temporary object to create a representation from
            tempObj=self.exportDeformedMesh(obj,'tempobj',False)
            
            kwargs[specialRepr]=specialReprs.deformedmesh
            kwargs[tempDS]=tempObj.datasets[0]
            
            rep= MeshScenePlugin.createRepr(self,tempObj,obj.deformReprType,refine,drawInternal,externalOnly,matname,**kwargs)
            rep.setName('DeformedMesh')
            rep.parent=obj
            rep.plugin=self
            obj.reprs.append(rep)
            
            return rep
            
        # create the handle line grid representation
        if obj.getCtrlPointRepr() is None:
               
            kwargs[specialRepr]=specialReprs.handlelines
            
            rep=MeshScenePlugin.createRepr(self,obj,reprtype,0,drawInternal,externalOnly,matname,**kwargs)
            rep.setName('ControlPointHandles')
            self.mgr.addFuncTask(lambda:self.mgr.showHandle(rep))
            return rep
        
        return None
    
    def _delayUpdateRepr(self,obj):
        '''Delayed method to auto-update the deformed mesh representation when a control point is moved.'''
        drep=first(r for r in obj.reprs if r.kwargs.get(specialRepr,'')==specialReprs.deformedmesh)
        
        if drep:
            f=self.updateDeformedRepr(obj)
            self.mgr.checkFutureResult(f)
    
    @delegatedmethod
    @taskmethod('Updating Deformed Representation')
    def updateDeformedRepr(self,obj,task=None):
        assert obj.plugin==self
        
        if not obj.reprs:
            raise ValueError('Deform object representation must be visible first')
            
        drep=first(r for r in obj.reprs if r.kwargs.get(specialRepr,'')==specialReprs.deformedmesh)
        
        newrep=obj.createRepr(deformRepr)
        
        if not drep:
            self.mgr.addSceneObjectRepr(newrep)
        elif obj.deformReprType!=drep.reprtype:
            self.mgr.removeSceneObjectRepr(drep)
            self.mgr.addSceneObjectRepr(newrep)
        else:
            obj.reprs.remove(newrep)
            drep.nodes[:]=newrep.nodes[:]
            
            self.mgr.updateSceneObjectRepr(drep)
    
    def updateObjPropBox(self,obj,prop):
        MeshScenePlugin.updateObjPropBox(self,obj,prop)
        deprop=prop.deprop
        
        objs=[o.getName() for o in self.mgr.objs if o is not obj and isinstance(o,MeshSceneObject)]
        
        eidolon.fillList(deprop.srcBox,objs,deprop.srcBox.currentIndex())
        
        deprop.setGridSize(*obj.ctrldims)
    
    def createObjPropBox(self,obj):
        prop=MeshScenePlugin.createObjPropBox(self,obj)
        
        deprop=DeformPropertyWidget()
        prop.deprop=deprop
        prop.layout().addWidget(prop.deprop)
        
        @deprop.volButton.toggled.connect
        def _setRepr(_):
            obj.deformReprType=deprop.getMeshType()

        @deprop.setButton.clicked.connect
        def _set():
            src=deprop.srcBox.currentText()
            sobj=first(o for o in self.mgr.objs if o.getName()==src)
            x,y,z=deprop.getGridSize()
            
            if not sobj:
                raise ValueError('No valid source mesh object found (name given as %r)'%src)
            
            f=obj.setSourceObj(sobj,x,y,z)
            self.mgr.checkFutureResult(f)
            
        @deprop.updateButton.clicked.connect
        def _update():
            f=self.updateDeformedRepr(obj)
            self.mgr.checkFutureResult(f)
            
        @deprop.exportButton.clicked.connect
        def _export():
            exobj=self.exportDeformedMesh(obj)
            self.mgr.checkFutureResult(exobj)
            self.mgr.addSceneObjectTask(exobj)

        return prop
    
    @delegatedmethod
    @taskmethod('Setting Source Object')
    def setSourceObj(self,defobj,source,dimx,dimy,dimz,task=None):
        defobj.sourceObj=source.getName()
        trans=transform()
        srcnodes=source.datasets[0].getNodes()
        
        if source.reprs:
            rep=source.reprs[0]
            trans=rep.getTransform()
            aabb=BoundBox([trans*n[0] for n in rep.nodes])
        else:
            aabb=BoundBox(srcnodes)
            
        if defobj.reprs:
            for r in defobj.reprs:
                self.mgr.removeSceneObjectRepr(r)
            
        defobj.setControlBox(aabb.minv,aabb.maxv,dimx,dimy,dimz)
        defobj.sourceXis=calculateNodeXis(srcnodes,trans,aabb,task)
        defobj.sourceCoeffs=calculateNodeCoeffs(defobj.sourceXis,dimx,dimy,dimz,task)
        
        rep=defobj.createRepr(ReprType._line)
        self.mgr.addSceneObjectRepr(rep)
    
    def _handleMoved(self,handle,isReleased):
        if isReleased:
            obj,ind=handle.value
            self.setControlPoint(obj,ind,handle.positionOffset)
    
    def setControlPoint(self,obj,ind,pos):
        obj.setControlPoint(ind,pos)
        
        ctrlrep=obj.getCtrlPointRepr()
        
        if ctrlrep:
            f=self.mgr.updateSceneObjectRepr(ctrlrep)
            self.mgr.checkFutureResult(f)
            self._delayUpdateRepr(obj)
            
    @taskmethod('Exporting Deformed Mesh')
    def exportDeformedMesh(self,obj,name=None,copyData=True,task=None):
        sobj=first(o for o in self.mgr.objs if o.getName()==obj.sourceObj)
        ctrlrep=obj.getCtrlPointRepr()
        name=name or (sobj.getName()+'_Deform')
        
        ctrls=obj.ctrls.clone('ctrlsclone')
        ctrls.mul(ctrlrep.getTransform() if ctrlrep else transform())
        
        ds=sobj.datasets[0].clone(tempDS,True,copyData,copyData)
        applyCoeffs(obj.sourceCoeffs,ctrls,ds.getNodes(),task)
        
        return MeshSceneObject(name,ds,None)
        
    @delegatedmethod
    def createHandles(self,rep,**kwargs):
        handles=MeshScenePlugin.createHandles(self,rep)
        
        if rep.kwargs.get('specialRepr','')==specialReprs.handlelines:
            pos=rep.getPosition()
            obj=rep.parent
            ctrls=obj.ctrls
            
            for ind in range(ctrls.n()):
                h=eidolon.NodeDragHandle(ctrls[ind]-pos,(obj,ind),self._handleMoved)
                handles.append(h)
        
        return handles
        
### Add plugin to environment

eidolon.addPlugin(DeformPlugin())
