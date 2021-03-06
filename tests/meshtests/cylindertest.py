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

from eidolon import *

m1=mgr.getMaterial('Default')

nodes=[vec3(0.1,0.2,0.3),vec3(0.5,0.2,1),vec3(1,0.4,2)]
inds=[(0,1,2)]
field=[0.5,0.7,1.0]

ds=PyDataSet('lineDS',nodes,[('lines',ElemType._Line2NL,inds)],[('field',field,'lines')])

obj=MeshSceneObject('line',ds)
mgr.addSceneObject(obj)

rep=obj.createRepr(ReprType._cylinder,30,radrefine=30,field='field')
mgr.addSceneObjectRepr(rep)

mgr.showBoundBox(rep) # draw a bound box around the vessels

# apply material, the alpha function is a linear function on the field, ie. the field's value
rep.applyMaterial(m1,field='field',alphafunc=UnitFunc.Linear) 

mgr.setCameraSeeAll()