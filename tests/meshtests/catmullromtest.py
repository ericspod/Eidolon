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

from eidolon import MeshSceneObject, ElemType, vec3, PyDataSet,ReprType,frange,successive


et=ElemType.Line1PCR
step=0.05
limits=[(0,1)]

ctrlnodes=[vec3(-1,0,1),vec3(0,0,0.5),vec3(0.75,0,0.75),vec3(1.2,0,-0.15)]

nodeobj=MeshSceneObject('ctrlnodes',PyDataSet('ds',ctrlnodes))
mgr.addSceneObject(nodeobj)

rep=nodeobj.createRepr(ReprType._glyph,glyphname='sphere',glyphscale=(0.5,0.5,0.5))
mgr.addSceneObjectRepr(rep)

mgr.setCameraSeeAll()


nodes=[et.applyBasis(ctrlnodes,xi,0,0,ul=len(ctrlnodes),limits=limits) for xi in frange(0,1+step,step)]
inds=list(successive(range(len(nodes))))

lineobj=MeshSceneObject('line',PyDataSet('ds',nodes,[('lines',ElemType._Line1NL,inds)]))
mgr.addSceneObject(lineobj)

rep=lineobj.createRepr(ReprType._cylinder,0,radrefine=5,radius=0.01)
mgr.addSceneObjectRepr(rep)
