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

from eidolon import MeshSceneObject,ElemType,vec3,listToMatrix,ReprType
from TestUtils import generateTestMeshDS

ds=generateTestMeshDS(ElemType._Tri1NL,4)
nodes=ds.getNodes()
dirs=listToMatrix([tuple(nodes.getAt(i)) for i in xrange(nodes.n())],'dirs' )
ds.setDataField(dirs)

obj=MeshSceneObject('Sphere',ds)
mgr.addSceneObject(obj)

rep=obj.createRepr(ReprType._point)
mgr.addSceneObjectRepr(rep)
rep.applyMaterial('Rainbow',field='dist')
rep.setScale(vec3(1.5))

rep1=obj.createRepr(ReprType._glyph,glyphname='sphere', sfield= 'dist',glyphscale=(0.015, 0.015, 0.015))
mgr.addSceneObjectRepr(rep1)
rep1.applyMaterial('Rainbow',field='dist')

rep2=obj.createRepr(ReprType._glyph,dfield='dirs',glyphname='arrow', glyphscale=(0.025, 0.025, 0.035))
mgr.addSceneObjectRepr(rep2)
rep2.setScale(vec3(0.75))
rep2.applyMaterial('Rainbow',field='dirs',valfunc='Average')

mgr.setCameraSeeAll()

