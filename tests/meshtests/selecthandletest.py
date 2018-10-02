
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
    h.append(NodeSelectHandle(nodes[ind],(ind,nodes),radiusQuery,print))
    
    return h

mgr.showHandle(rep,True)

