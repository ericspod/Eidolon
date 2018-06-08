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

from eidolon import ReprType, vec3

dds=Dicom.loadDirDataset(scriptdir+'/DicomData')

series='1.3.6.1.4.1.9590.100.1.1.2375764972290531328210423958986997132495'

# load the image object
obj=Dicom.loadSeries(dds.getSeries(series))
mgr.addSceneObject(obj)

# create the volume representation
rep=obj.createRepr(ReprType._imgtimevolume)
mgr.addSceneObjectRepr(rep)

# create the plane object
plane=SlicePlugin.createSlicePlane(rep.getAABB().center,vec3(0,0,1))
mgr.addSceneObject(plane)

# create a line representation of the plane and show its handle
prep=plane.createRepr(ReprType._line)
mgr.addSceneObjectRepr(prep)
mgr.showHandle(prep)

plane.setApplyToRepr(rep) # apply the plane to the representation

mgr.controller.setPosition(vec3(92,-41,-41))
mgr.controller.setRotation(2.3,0.45)
mgr.controller.setZoom(700)
mgr.setCameraSeeAll()

