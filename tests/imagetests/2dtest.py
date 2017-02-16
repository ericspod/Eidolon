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
from Testing import ImageSceneObject, generateSphereImageStack, ReprType,delayedcall

images=generateSphereImageStack(50,50,50)
obj=ImageSceneObject('Sphere',[],images)
mgr.addSceneObject(obj)

rep=obj.createRepr(ReprType._imgstack)
mgr.addSceneObjectRepr(rep)

mgr.setCameraSeeAll()

d1=mgr.create2DView()
mgr.callThreadSafe(d1.setImageStackPosition,25)

d2=mgr.create2DView()
mgr.callThreadSafe(d2.setImageStackPosition,25)

# wait for 1 second, remove the second 2d window and then add a third
@mgr.addFuncTask
@delayedcall(1.0)
def _remove():
	d2.parentWidget().close()
	d3=mgr.create2DView()
	d3.setImageStackPosition(25)
