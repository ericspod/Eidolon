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

from eidolon import ReprType, AxesType, ElemType, color

rootdir=scriptdir+'/MeshData' 

m1=mgr.cloneMaterial('Default') # create a semitransparent material
m1.setAlpha(0.5)

m2=mgr.cloneMaterial('Default') # create a point material
m2.setPointSizeAbs(3.0)
m2.useLighting(False)
m2.useDepthCheck(False)
m2.setDiffuse(color(0.75,0,0))

obj=CHeart.loadSceneObject(rootdir+'/1d_FE.X',rootdir+'/1d_FE.T',ElemType._Line2NL) # load the vessels
df=obj.loadDataField(rootdir+'/1d_rad_avg_FE.D',1) # load per-node radius data

mgr.addSceneObject(obj)

# create a cylinder representation type, using 'df' as the radius field
rep=obj.createRepr(ReprType._cylinder,30,radrefine=5,field=df)
mgr.addSceneObjectRepr(rep)
mgr.showBoundBox(rep) # draw a bound box around the vessels
rep.applyMaterial(m1)

# create a representation type plotting the vessel lines, this will draw over the cylinders since m2 doesn't depth check
rep=obj.createRepr(ReprType._line,20)
mgr.addSceneObjectRepr(rep)
rep.applyMaterial(m2)

# create a representation type plotting the control nodes
rep=obj.createRepr(ReprType._node)
mgr.addSceneObjectRepr(rep)
rep.applyMaterial(m2)

mgr.setAxesType(AxesType._cornerTR) # top right corner axes
mgr.controller.setRotation(0.8,0.8)
mgr.setCameraSeeAll()
