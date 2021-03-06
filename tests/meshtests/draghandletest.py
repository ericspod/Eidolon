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

from eidolon import(
        vec3, color, ElemType, PyDataSet, ReprType, MeshSceneObject,NodeDragHandle,setmethod,
        FT_LINELIST,PyVertexBuffer,PyIndexBuffer
        )

# construct a dataset with a single triangle by defining 3 vertices, an index matrix with 1 element, and a field assigning a value to each vertex
nodes=[vec3(0,0,0),vec3(1,0,0),vec3(0.5,0,0.866)] # 3 vertices of triangle
inds=[(0,1,2)] # single element in index matrix
field=[0.0,1.0,2.0]
ds=PyDataSet('TriDS',nodes,[('triind',ElemType._Tri1NL,inds)],[('vals',field,'triind')])

# create the scene object which contains the dataset
obj=MeshSceneObject('Tri',ds)
mgr.addSceneObject(obj)

# create a visual representation of the triangle, "volume" in this value referring to a 3D representation
rep=obj.createRepr(ReprType._volume,0)
mgr.addSceneObjectRepr(rep)
rep.applyMaterial('Rainbow',field='vals')

# adjust the camera to get the triangle in frame
mgr.setCameraSeeAll()


#create the figure for the triangle line, this object will be called linefig
@mgr.callThreadSafe
def linefig():
    vbuf=PyVertexBuffer(nodes,[vec3()]*len(nodes),[color(0,1,1,1)]*len(nodes))
    ibuf=PyIndexBuffer([(0,1),(1,2),(2,0)])

    fig=mgr.scene.createFigure('line','Default',FT_LINELIST)
    fig.fillData(vbuf,ibuf)
    fig.setOverlay(True)
    fig.setVisible(True)
    return fig


def dragCallback(handle,isReleased):
    nodes[handle.value]=handle.getAbsolutePosition()
    print(handle,handle.value,isReleased)
    vbuf=PyVertexBuffer(nodes,[vec3()]*len(nodes),[color(0,1,1,1)]*len(nodes))
    ibuf=PyIndexBuffer([(0,1),(1,2),(2,0)])
    linefig.fillData(vbuf,ibuf)


# replace the method for creating handles for rep to return the transform handle plus the drag handles
@setmethod(rep)
def createHandles():
    h= rep.__old__createHandles()
    
    for i,n in enumerate(nodes):
        h.append(NodeDragHandle(n,i,dragCallback))
    
    return h

mgr.showHandle(rep,True)
