
from eidolon import ReprType,AxesType

dds=Dicom.loadDirDataset(scriptdir+'/DicomData') # load the Dicom files from this directory, returns a DicomDataset object

series='1.3.6.1.4.1.9590.100.1.1.2375764972290531328210423958986997132495' # series UID values are stored in the Dicom files

obj=Dicom.loadSeries(series) # load the series, this produces a ImageSceneObject object

mgr.addSceneObject(obj)

rep=obj.createRepr(ReprType._imgtimestack) # this image has timesteps so load a time stack
mgr.addSceneObjectRepr(rep)
mgr.showBoundBox(rep)

mgr.controller.setRotation(-2,0.5)
mgr.setAxesType(AxesType._originarrows)
mgr.setCameraSeeAll()
