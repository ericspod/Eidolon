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
        MeshSceneObject,MeshScenePlugin, ElemType, PyDataSet, Vec3Matrix,IndexMatrix, RealMatrix, BoundBox, vec3, 
        NodeDragHandle,
        chooseProcCount, delegatedmethod
)

gridType=ElemType.Hex1PCR

    
@eidolon.concurrent
def calculateNodeXisRange(process,nodes,xis,minv,diff):
    for n in process.prange():
        xi=(nodes[n]-minv)/diff
        xis[n]=tuple(xi)


def calculateNodeXis(nodes,boundbox=None,task=None):
    boundbox=boundbox or BoundBox(nodes)
    minv=boundbox.minv
    maxv=boundbox.maxv
    diff=maxv-minv
    
    assert not diff.isZero()
    
    proccount=chooseProcCount(len(nodes),0,1000)
    nodes.setShared(proccount!=1)
    xis=eidolon.RealMatrix('xis',len(nodes),3,proccount!=1)
    

    calculateNodeXisRange(len(nodes),proccount,task,nodes,xis,minv,diff)
        
    return xis


@eidolon.concurrent
def calculateNodeCoeffsRange(process,xis,wpts,hpts,dpts):
    coeffs=[]
    
    for n in process.prange():
        x,y,z=xis[n]
        ncoeffs=gridType.basis(x,y,z,wpts,hpts,dpts)
        coeffs.append({i:v for i,v in enumerate(ncoeffs) if eidolon.epsilonZero(v)!=0})
        
    return coeffs


def calculateNodeCoeffs(xis,wpts,hpts,dpts,task=None):
    proccount=chooseProcCount(len(xis),0,1000)
    if proccount!=1:
        eidolon.shareMatrices(xis)
    
    result=calculateNodeCoeffsRange(xis.n(),proccount,task,xis,wpts,hpts,dpts)
    
    eidolon.checkResultMap(result)
    
    return eidolon.sumResultMap(result)


@eidolon.concurrent
def applyCoeffsRange(process,coeffs,ctrlpts,outnodes):
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
        eidolon.shareMatrices(outnodes)
        
    applyCoeffsRange(outnodes.n(),proccount,task,coeffs,ctrlpts,outnodes)
    
    return outnodes
    

def generateControlBox(bbmin,bbmax,dimx,dimy,dimz):
    nodes,hexes=eidolon.generateHexBox(dimx-2,dimy-2,dimz-2) # generate a hex grid
    _,lineinds=eidolon.generateLineBox((bbmin,bbmax)) # get indices for a line box
    
    bbdiff=bbmax-bbmin
    nodes=[n*bbdiff+bbmin for n in nodes]
    lines=set()
    
    # convert hexes into line indices joining the edges
    for h in hexes:
        for i,j in lineinds:
            lines.add((h[i],h[j]))
            
    return nodes,sorted(lines)
    

class DeformSceneObject(MeshSceneObject):
    def __init__(self,name,plugin=None,**kwargs):
        self.ctrls=Vec3Matrix('ctrl',1)
        self.ctrldims=(1,1,1)
        self.lineinds=IndexMatrix('lines',ElemType._Line1NL,1,2)
        self.sourceObj=None
        self.sourceCoeffs=None
        self.sourceXis=None
        
        dataset=PyDataSet('ctrls',self.ctrls,[self.lineinds])
        
        MeshSceneObject.__init__(self,name,dataset,plugin)
    
    def setControlBox(self,bbmin,bbmax,dimx,dimy,dimz):
        nodes,lines=generateControlBox(bbmin,bbmax,dimx,dimy,dimz)
        self.ctrldims=(dimx,dimy,dimz)
        
        self.ctrls.setN(len(nodes))
        self.ctrls[:]=nodes
        self.lineinds.setN(len(lines))
        self.lineinds[:]=lines
    

class DeformPlugin(MeshScenePlugin):
    def __init__(self):
        MeshScenePlugin.__init__(self,'Deform')

    def init(self,plugid,win,mgr):
        MeshScenePlugin.init(self,plugid,win,mgr)
        
    def createRepr(self,obj,reprtype,refine=0,drawInternal=False,externalOnly=True,matname='Default',**kwargs):
        MeshScenePlugin.createRepr(self,obj,reprtype,0,drawInternal,externalOnly,matname,**kwargs)
        
    def setControlPoint(self,handle,isRelease):
        if isRelease:
            obj,ind=handle.value
            obj.nodes[ind]=handle.getAbsolutePosition()
        
    @delegatedmethod
    def createHandles(self,rep,**kwargs):
        handles=MeshScenePlugin.createHandles(rep)
        
        nodes=rep.nodes
        pos=rep.getPosition()
        
        
        
        
        return handles
        
### Add plugin to environment

eidolon.addPlugin(DeformPlugin())
