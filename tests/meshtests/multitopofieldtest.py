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

import sys
sys.path.append(scriptdir+'..')
from eidolon import MeshSceneObject,ElemType,vec3,color,ReprType,frange,PyDataSet

mat=mgr.getMaterial('Rainbow')
mat.setSpectrumValue(1,0.005,color(0.0,1.0,1.0,1.0))

trinodes=[vec3(0,0,0),vec3(1,0,0),vec3(0.5,0,1),vec3(1.1,0,0),vec3(2.1,0,0),vec3(1.6,0,1)]
triinds=[(0,1,2),(3,4,5)]
trifield=[1,2,3,4,5,6]
trielemfield=[-1,2]

quadnodes=[vec3(2.2,0,0),vec3(3.2,0,0),vec3(2.2,0,1),vec3(3.2,0,1),vec3(3.3,0,0),vec3(4.3,0,0),vec3(3.3,0,1),vec3(4.3,0,1)]
quadinds=[(6,7,8,9),(10,11,12,13)]
quadfield=[1,2,3,4,5,6,7,8]
quadelemfield=[-1,2]
quadfieldtopo=[(0,1,2,3),(4,5,6,7)] # need a separate topology for quad field since the quad topo doesn't start indexing from 0

nodes=trinodes+quadnodes

nodefield=list(frange(len(nodes)))

inds=[
    ('tris',ElemType._Tri1NL,triinds),
    ('quads',ElemType._Quad1NL,quadinds),
    ('quadfieldtopo',ElemType._Quad1NL,quadfieldtopo,False)
]

fields=[
    ('trifield',trifield,'tris'), # per-vertex field for triangles
    ('trielemfield',trielemfield,'tris'), # per-element field for triangles
    ('quadfield',quadfield,'quads','quadfieldtopo'), # per-vertex field for quads
    ('quadelemfield',quadelemfield,'quads'), # per-element field for quads
    ('nodefield',nodefield) # per-node field for whole mesh
]

ds=PyDataSet('MeshTest',nodes,inds,fields)

obj=MeshSceneObject('Test',ds)
mgr.addSceneObject(obj)

# render the triangle field
rep=obj.createRepr(ReprType._volume,0)
mgr.addSceneObjectRepr(rep)
rep.applyMaterial(mat,field='trifield')

# render the quad field
rep=obj.createRepr(ReprType._volume,10)
mgr.addSceneObjectRepr(rep)
rep.setPosition(vec3(0,0,-1.1))
rep.applyMaterial(mat,field='quadfield')

# render the per-elem triangle field
rep=obj.createRepr(ReprType._volume,10)
mgr.addSceneObjectRepr(rep)
rep.setPosition(vec3(0,0,-2.2))
rep.applyMaterial(mat,field='trielemfield')

# render the per-elem quad field
rep=obj.createRepr(ReprType._volume,10)
mgr.addSceneObjectRepr(rep)
rep.setPosition(vec3(0,0,-3.3))
rep.applyMaterial(mat,field='quadelemfield')

# render the per-node field
rep=obj.createRepr(ReprType._volume,10)
mgr.addSceneObjectRepr(rep)
rep.setPosition(vec3(0,0,-4.4))
rep.applyMaterial(mat,field='nodefield')

mgr.setCameraSeeAll()
