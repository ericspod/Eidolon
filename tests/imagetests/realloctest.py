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
from Testing import ReprType,generateTimeSphereImages,ImageSceneObject,extendImage

step=0.1
dim=50

# create an object and repr with a particular name

images=generateTimeSphereImages(step,dim)
obj=ImageSceneObject('Sphere',[],images)
mgr.addSceneObject(obj)

rep=obj.createRepr(ReprType._imgtimevolume)
mgr.addSceneObjectRepr(rep)

del obj
del rep

mgr.clearScene() # this should free up existing objects

# attempt to create an object and repr with the same name as the above, this will crash if the repr doesn't choose unique names for materials, textures, etc.

images=generateTimeSphereImages(step,dim)
obj=ImageSceneObject('Sphere',[],images)
mgr.addSceneObject(obj)

rep=obj.createRepr(ReprType._imgtimevolume)
mgr.addSceneObjectRepr(rep)

mgr.setCameraSeeAll()
