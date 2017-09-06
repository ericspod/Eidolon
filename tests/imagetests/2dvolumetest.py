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

from eidolon import ImageSceneObject, generateSphereImageStack, ReprType,vec3

images=generateSphereImageStack(50,50,50)
obj=ImageSceneObject('Sphere',[],images)
mgr.addSceneObject(obj)

rep1=obj.createRepr(ReprType._imgvolume)
mgr.addSceneObjectRepr(rep1)

mgr.callThreadSafe(rep1.applySpectrum,mgr.getSpectrum('BW'))

rep1.setPosition(vec3(5,-10,-4))
rep1.setRotation(0.1,0.2,-0.12)

#rep2=obj.createRepr(ReprType._imgstack)
#mgr.addSceneObjectRepr(rep2)
#
#rep2.setPosition(vec3(5,-10,-4))
#rep2.setRotation(0.1,0.2,-0.12)

mgr.setCameraSeeAll()

d1=mgr.create2DView()
mgr.callThreadSafe(d1.setImageStackPosition,250)
