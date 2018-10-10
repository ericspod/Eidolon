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

from eidolon import ReprType,AxesType

dds=Dicom.loadDirDataset(scriptdir+'/DicomData') # load the Dicom files from this directory, returns a DicomDataset object

series='1.3.6.1.4.1.9590.100.1.1.2375764972290531328210423958986997132495' # series UID values are stored in the Dicom files

obj=Dicom.loadSeries(series) # load the series, this produces a ImageSceneObject object

#mgr.addSceneObject(obj)
#
#rep=obj.createRepr(ReprType._imgtimestack) # this image has timesteps so load a time stack
#mgr.addSceneObjectRepr(rep)
#mgr.showBoundBox(rep)
#
#mgr.controller.setRotation(-2,0.5)
#mgr.setAxesType(AxesType._originarrows)
#mgr.setCameraSeeAll()

mgr.quit()
