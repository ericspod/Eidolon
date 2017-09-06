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
from eidolon import ReprType,ImageSceneObject,vec3,rotator,PT_FRAGMENT
from TestUtils import generateTimeSphereImages

step=0.1

images=generateTimeSphereImages(step)
obj=ImageSceneObject('Sphere',[],images)
mgr.addSceneObject(obj)

rep=obj.createRepr(ReprType._imgtimestack)
mgr.addSceneObjectRepr(rep)
rep.setPosition(vec3(5,-10,-4))
rep.setRotation(0.1,0.2,-0.12)

rep1=obj.createRepr(ReprType._imgtimevolume)
mgr.addSceneObjectRepr(rep1)
rep1.setPosition(vec3(61,6,8))
rep1.setRotation(-0.1,-0.13,0.22)

obj1 = SlicePlugin.createSliceBox(vec3(55.5,-25.0,24.5),vec3(25.0),(0, 0.33495133768504726, 0.22227234443175778))
mgr.addSceneObject(obj1)

rep2 = obj1.createRepr(ReprType._line)
mgr.addSceneObjectRepr(rep2)
mgr.showHandle(rep2,True)

obj1.setApplyToRepr(rep)
obj1.setApplyToRepr(rep1)

mgr.setCameraSeeAll()
