# Eidolon Biomedical Framework
# Copyright (C) 2016 Eric Kerfoot, King's College London, all rights reserved
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
from Testing import MeshSceneObject,ElemType,ReprType,vec3,generateTestMeshDS

ds=generateTestMeshDS(ElemType._Tet2NL,7)

obj=MeshSceneObject('Tets',ds)
mgr.addSceneObject(obj)

rep=obj.createRepr(ReprType._node)
mgr.addSceneObjectRepr(rep)
rep.applyMaterial('Rainbow',field='dist')

rep=obj.createRepr(ReprType._point,2,drawInternal=True,externalOnly=False)
mgr.addSceneObjectRepr(rep)
rep.applyMaterial('Rainbow',field='dist')
rep.setPosition(vec3(1.1,0,0))

rep=obj.createRepr(ReprType._line,2,drawInternal=True,externalOnly=False)
mgr.addSceneObjectRepr(rep)
rep.applyMaterial('Rainbow',field='dist')
rep.setPosition(vec3(0,0,-1.1))

rep=obj.createRepr(ReprType._volume,2,drawInternal=True,externalOnly=False)
mgr.addSceneObjectRepr(rep)
rep.applyMaterial('Rainbow',field='dist')
rep.setPosition(vec3(1.1,0,-1.1))

mgr.setCameraSeeAll()


