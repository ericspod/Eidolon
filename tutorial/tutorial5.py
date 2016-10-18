
from eidolon import ElemType, ReprType, AxesType

root=scriptdir+'/MeshData'

# load all of the spatial timesteps
obj=CHeart.loadSceneObject(['%s/LinBox%.4i.X'%(root,i) for i in range(10)],root+'/LinBox.T',ElemType._Hex1NL)

# load a field timestep for each spatial step, if there is more than one spatial timestep, the number of field timesteps must be the same
dfs=obj.loadDataField(['%s/LinBox_LenSq%.4i.D'%(root,i) for i in range(10)],1)

mgr.addSceneObject(obj)

rep=obj.createRepr(ReprType._volume,10,externalOnly=True)
mgr.addSceneObjectRepr(rep)

mgr.setCameraSeeAll()
mgr.controller.setRotation(-0.6,0.6)
mgr.setAxesType(AxesType._cornerTR)

m=mgr.getMaterial('Rainbow')
rep.setDataField('LenSq')
rep.applyMaterial(m) # alternatively use field=dfs as an argument instead of setting the field in the previous line
