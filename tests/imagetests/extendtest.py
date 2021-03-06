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
from eidolon import ReprType,ImageSceneObject,extendImage
from TestUtils import generateTimeSphereImages

step=0.1
dim=30
mx=2
my=3
mz=4
fillVal=3.0

images=generateTimeSphereImages(step,dim)
obj=ImageSceneObject('Sphere',[],images)
mgr.addSceneObject(obj)

obj1=extendImage(obj,'ext',mx,my,mz,fillVal)
mgr.addSceneObject(obj1)

rep=obj1.createRepr(ReprType._imgtimestack)
mgr.addSceneObjectRepr(rep)

mgr.setCameraSeeAll()
