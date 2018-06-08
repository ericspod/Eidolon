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

from eidolon import MeshSceneObject,ImageSceneObject,ElemType,ReprType
from TestUtils import generateTimeSphereImages,generateTimeSphereMeshes

step=0.1

images=generateTimeSphereImages(step)
obj=ImageSceneObject('Sphere',[],images)
mgr.addSceneObject(obj)

rep=obj.createRepr(ReprType._imgtimestack)
mgr.addSceneObjectRepr(rep)

dds,steps=generateTimeSphereMeshes(step)
obj1=MeshSceneObject('Sphere',dds)
obj1.setTimestepList(steps)
mgr.addSceneObject(obj1)

rep1=obj1.createRepr(ReprType._volume,0)
mgr.addSceneObjectRepr(rep1)
rep1.applyMaterial('Rainbow',field='dist')

d=mgr.create2DView()

@mgr.callThreadSafe
def _set():
    d.setSecondary(rep1.getName(),True)
    d.setImageStackPosition(24)

mgr.setCameraSeeAll()
