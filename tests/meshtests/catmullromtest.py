
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
