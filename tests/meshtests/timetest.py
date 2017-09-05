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

import sys,math
sys.path.append(scriptdir+'..')

from eidolon import MeshSceneObject,ElemType,ReprType,vec3,frange
from TestUtils import generateTestMeshDS

dds=[]
for i in frange(0,1,0.05):
    i=math.sin(i*math.pi*2)
    ds=generateTestMeshDS(ElemType._Tri1NL,5)
    nodes=ds.getNodes()
    nodes.mul(vec3(2.0+i,1.0,2.0-i))

    dist=ds.getDataField('dist')
    for n in xrange(dist.n()):
        dist.setAt(nodes.getAt(n).distTo(vec3(0.25)),n)

    dds.append(ds)

obj=MeshSceneObject('Sphere',dds)
mgr.addSceneObject(obj)
obj.setTimestepList(list(frange(0,1,0.05)))

rep=obj.createRepr(ReprType._volume,0)
mgr.addSceneObjectRepr(rep)

mgr.setCameraSeeAll()

rep.applyMaterial('Rainbow',field='dist')

mgr.setTimeStepsPerSec(1)
mgr.setTimeFPS(60)
mgr.play()
