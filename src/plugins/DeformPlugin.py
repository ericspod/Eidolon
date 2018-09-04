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
        MeshSceneObject,MeshScenePlugin, ElemType, RealMatrix, BoundBox, vec3, chooseProcCount, delegatedmethod
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
def calculateNodeCoeffsRange(process,xis,wpts,hpts,dpts,coeffs):
    for n in process.prange():
        x,y,z=xis[n]
        coeffs[n]=gridType.basis(x,y,z,wpts,hpts,dpts)
        

def calculateNodeCoeffs(xis,wpts,hpts,dpts,coeffs,task=None):
    proccount=chooseProcCount(len(xis),0,1000)
    xis.setShared(proccount!=1)
    
    if not coeffs:
        coeffs=RealMatrix('coeffs',xis.n(),wpts*hpts*dpts,proccount!=1)
    else:
        coeffs.setShared(proccount!=1)
    
    calculateNodeCoeffsRange(xis.n(),proccount,task,xis,wpts,hpts,dpts,coeffs)
    
    return coeffs


@eidolon.concurrent
def applyCoeffsRange(process,coeffs,ctrlpts,outnodes):
    for n in process.prange():
        outnodes[n]=ElemType.Point.applyCoeffs(ctrlpts,coeffs[n])
        

def applyCoeffs(coeffs,ctrlpts,outnodes,task=None):
    proccount=chooseProcCount(len(coeffs),0,1000)
    coeffs.setShared(proccount!=1)
    
    if not outnodes:
        outnodes=eidolon.Vec3Matrix('nodes',coeffs.n(),1,proccount!=1)
    else:
        outnodes.setShared(proccount!=1)
        
    applyCoeffsRange(coeffs.n(),proccount,task,coeffs,ctrlpts,outnodes)
    
    return outnodes
    

#class DeformSceneObject(MeshSceneObject):
    

class DeformPlugin(MeshScenePlugin):
    def __init__(self):
        MeshScenePlugin.__init__(self,'Deform')

    def init(self,plugid,win,mgr):
        MeshScenePlugin.init(self,plugid,win,mgr)
        
    @delegatedmethod
    def createHandles(self,rep,**kwargs):
        handles=MeshScenePlugin.createHandles(rep)
        
        return handles
        
### Add plugin to environment

eidolon.addPlugin(DeformPlugin())
