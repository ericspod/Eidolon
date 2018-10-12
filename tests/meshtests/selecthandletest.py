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

from eidolon import vec3, rotator, MeshSceneObject, PyDataSet, NodeSelectHandle, ReprType, halfpi, generatePlane, setmethod

import numpy as np
from scipy.spatial import cKDTree
                
    
nodes,_,_=generatePlane(4)

r=rotator(vec3.X(),halfpi)
nodes=[r*n for n in nodes]

obj=MeshSceneObject('nodes',PyDataSet('ds',nodes,[],[]))
mgr.addSceneObject(obj)

rep=obj.createRepr(ReprType._glyph,0,externalOnly=False,drawInternal=True,glyphname='sphere',glyphscale=(0.1,0.1,0.1))
mgr.addSceneObjectRepr(rep)

mgr.setCameraSeeAll()

tree=cKDTree(np.asarray(list(map(tuple,nodes))))

def radiusQuery(pos,radius):
    return tree.query_ball_point(tuple(pos),radius),tree.data


@setmethod(rep)
def createHandles():
    h= rep.__old__createHandles()
    
    ind=15
    h.append(NodeSelectHandle(nodes[ind],(ind,nodes),radiusQuery,print,'Select Handle'))
    
    return h

mgr.showHandle(rep,True)

