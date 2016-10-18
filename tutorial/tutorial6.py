
from eidolon import ReprType, vec3

dds=Dicom.loadDirDataset(scriptdir+'/DicomData')

series='1.3.6.1.4.1.9590.100.1.1.2375764972290531328210423958986997132495'

# load the image object
obj=Dicom.loadSeries(dds.getSeries(series))
mgr.addSceneObject(obj)

# create the volume representation
rep=obj.createRepr(ReprType._imgtimevolume)
mgr.addSceneObjectRepr(rep)

# create the plane object
plane=SlicePlugin.createSlicePlane(rep.getAABB().center,vec3(0,0,1))
mgr.addSceneObject(plane)

# create a line representation of the plane and show its handle
prep=plane.createRepr(ReprType._line)
mgr.addSceneObjectRepr(prep)
mgr.showHandle(prep)

plane.setApplyToRepr(rep) # apply the plane to the representation

mgr.controller.setPosition(vec3(92,-41,-41))
mgr.controller.setRotation(2.3,0.45)
mgr.controller.setZoom(700)
mgr.setCameraSeeAll()

