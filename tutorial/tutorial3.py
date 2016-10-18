
from eidolon import ElemType, ReprType, VecFunc, AxesType, ValueFunc, vec3

rootdir=scriptdir+'/MeshData' 

m=mgr.getMaterial('Rainbow')

obj=CHeart.loadSceneObject(rootdir+'/BORE_FE.X',rootdir+'/BORE_FE.T',ElemType._Tet1NL)

# load a field with it's own topology which is a different order than the spatial topology
df=obj.loadDataField(rootdir+'/Vel-1.D',3,rootdir+'/VBORE_FE.T',ElemType._Tet2NL)

mgr.addSceneObject(obj)

rep=obj.createRepr(ReprType._line,externalOnly=True) # create external lines
mgr.addSceneObjectRepr(rep)

# Create a glyph representation which uses the inbuilt arrow figure, uses df as the field to define arrow direction, uses df again for the scaling 
# field to indicate size, uses ZAxis as the scaling function to scale the arrows lengthwise only, and scales all the glyphs by an attractive factor
rep=obj.createRepr(ReprType._glyph,5,externalOnly=False,drawInternal=True,glyphname='arrow',dfield=df,vecfunc=VecFunc.Linear,sfield=df,scalefunc=VecFunc.ZAxis,glyphscale=(0.0025,0.0025,0.01))

mgr.addSceneObjectRepr(rep)

rep.applyMaterial(m,field=df,valfunc=ValueFunc.Magnitude) # colourize the representation using the same field, applying the magnitude function to each interpolated field value

mgr.setAxesType(AxesType._cornerTR) # show the axes in the top right corner of the 3D window
mgr.controller.setRotation(0.8,0.8) # move the camera to a nice angle
mgr.setCameraSeeAll()

