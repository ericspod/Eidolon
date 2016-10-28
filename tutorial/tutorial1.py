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

from eidolon import ElemType, ReprType # import the symbols we'll need

rootdir=scriptdir+'/MeshData' # scriptdir is a variable introduced by the runtime when a script is executed and is set to the path of the script's directory

# acquire the plugin and ask it to load a scene object
obj=CHeart.loadSceneObject(rootdir+'/linmesh_FE.X',rootdir+'/linmesh_FE.T',ElemType._Hex1NL)

# load a data field which has 1 value per line and no topology; the spatial topology of the scene object will be used as the field topology
df=obj.loadDataField(rootdir+'/linmesh_dist.D',1)

# add the object to the scene
mgr.addSceneObject(obj)

# create a volume representation which is not refined and represents the external surface only
rep=obj.createRepr(ReprType._volume,0,externalOnly=True)

# add the representation to the scene
mgr.addSceneObjectRepr(rep)

mgr.setCameraSeeAll() # set the camera viewing parameters to match the object's size
mgr.controller.setRotation(1.0,1.0) # rotate the camera slightly

m=mgr.getMaterial('Rainbow') # acquire this pre-existing material

# use the material to set properties and calculate a colour map (using the values of field 'df') for the representation
rep.applyMaterial(m,field=df)

mgr.saveScreenshot('screen.png') # take a pretty picture


