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

import sys
sys.path.append(scriptdir+'..')


from eidolon import MeshSceneObject,ElemType,ReprType
from TestUtils import generateTestMeshDS

ds=generateTestMeshDS(ElemType._Hex1NL,5)

obj=MeshSceneObject('Hexes',ds)
mgr.addSceneObject(obj)

#rep=obj.createRepr(ReprType._volume)
#mgr.addSceneObjectRepr(rep)
#rep.applyMaterial('Rainbow',field='dist')

de=Deform.createDeformObject()
mgr.addSceneObject(de)

de.setSourceObj(obj,3,3,3)



#rep=de.createRepr(ReprType._line)
#mgr.addSceneObjectRepr(rep)


mgr.setCameraSeeAll()
