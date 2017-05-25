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

import sys
sys.path.append(scriptdir+'..')
from Testing import MeshSceneObject,ElemType,vec3,ReprType,generateTestMeshDS

materials=['Red','Green','Blue','Magenta','Cyan']

for i in range(5):
    ds=generateTestMeshDS(ElemType._Tri1NL,i)

    obj=MeshSceneObject('Sphere'+str(i),ds)
    mgr.addSceneObject(obj)

    rep=obj.createRepr(ReprType._line,0)
    mgr.addSceneObjectRepr(rep)
    rep.setPosition(vec3(2.2*i,0,0))
    rep.applyMaterial(materials[i])

    rep=obj.createRepr(ReprType._cylinder,0,radrefine=5,radius=0.005)
    mgr.addSceneObjectRepr(rep)
    rep.setPosition(vec3(2.2*i,0,2.2))
    rep.applyMaterial(materials[i])

mgr.setCameraSeeAll()

