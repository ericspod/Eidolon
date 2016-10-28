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
from Testing import ReprType,generateSphereImageStack,ImageSceneObject,vec3

images=generateSphereImageStack(50,50,50,vec3(0.5,0.5,1),vec3(0.45,0.45,0.9))
obj=ImageSceneObject('Sphere',[],images)
mgr.addSceneObject(obj)

rep=obj.createRepr(ReprType._imgvolume)
mgr.addSceneObjectRepr(rep)

mgr.setCameraSeeAll()
