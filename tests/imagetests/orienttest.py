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

from eidolon import ReprType,vec3, rotator,generateArrow,halfpi, MeshSceneObject,TriDataSet,AxesType

pos=vec3(-10,20,-15)
rot=rotator(0.1,-0.2,0.13)
w,h,d=31,42,53

nodesz,indsz=generateArrow(5)
nodesz=[(n+vec3.Z())*vec3(w,d,h)*vec3(0.1,0.1,0.5) for n in nodesz]
nodesx=[rotator(vec3(0,1,0),halfpi)*n for n in nodesz]
nodesy=[rotator(vec3(1,0,0),-halfpi)*n for n in nodesz]

nodes=[(rot*n)+pos for n in (nodesx+nodesy+nodesz)]
nlen=len(nodesz)
indices=indsz+[(i+nlen,j+nlen,k+nlen) for i,j,k in indsz]+[(i+nlen*2,j+nlen*2,k+nlen*2) for i,j,k in indsz]
field=[2.0]*nlen+[1.0]*nlen+[0.0]*nlen

axes=MeshSceneObject('Axes',TriDataSet('tris',nodes,indices,[('col',field)]))
mgr.addSceneObject(axes)

arep=axes.createRepr(ReprType._volume)
mgr.addSceneObjectRepr(arep)
arep.applyMaterial('Rainbow',field='col')


obj=ImgPlugin.createTestImage(w,d,h,1,pos,rot)
mgr.addSceneObject(obj)

rep=obj.createRepr(ReprType._imgstack)
mgr.addSceneObjectRepr(rep)

rep.useTexFiltering(False)

mgr.setCameraSeeAll()
mgr.setAxesType(AxesType._cornerTL)

d=mgr.create2DView()

@mgr.callThreadSafe
def _set():
    d.setSecondary(arep.getName(),True)
    d.setImageStackPosition(1)
