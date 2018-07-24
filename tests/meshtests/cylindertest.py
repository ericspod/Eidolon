
from eidolon import *

m1=mgr.getMaterial('Rainbow')

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