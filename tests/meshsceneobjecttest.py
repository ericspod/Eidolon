import numpy as np

from eidolon.renderer import Light, LightType, OffscreenCamera
from eidolon.ui import MainWindow, init_ui, exec_ui, load_rc_file, CameraWidget
from eidolon import config
from eidolon.mathdef import vec3, Mesh, ElemType
from eidolon.scene import ReprType, MeshSceneObject, QtCameraController, MeshScenePlugin, SceneManager

# win = SimpleApp(1200, 800)

conf = config.load_config()

app = init_ui()

app.setStyle("plastique")
sheet = load_rc_file("DefaultUIStyle", ":/css").decode('utf-8')

app.setStyleSheet(sheet)

win = MainWindow(conf)
mgr = SceneManager.init({}, win)

cam = OffscreenCamera("test", 400, 400)
mgr.cameras.append(cam)

camwidget = CameraWidget(cam, events=mgr.evt_dispatch)

mgr.controller = QtCameraController(cam, vec3.zero, 0, 0, 50)
mgr.controller.attach_events(camwidget.events)

win.setCentralWidget(camwidget)

dat = np.load("data/linmesh.npz")

mesh = Mesh(dat["x"], {"inds": (dat["t"] - 1, ElemType._Hex1NL)}, {"field": (dat["d"], "inds")})

obj = MeshSceneObject("linmesh", [mesh], mgr.get_plugin("Mesh"))
mgr.add_scene_object(obj)

repr = obj.plugin.create_repr(obj, ReprType._volume)
mgr.add_scene_object_repr(repr)

mgr.controller.set_camera_see_all()

light = Light("dlight", LightType.DIRECTIONAL, (0.5, 0.5, 0.5, 1))
light.attach(cam, True)

amb = Light("amb", LightType.AMBIENT, (0.25, 0.25, 0.25, 1))
amb.attach(cam)

exec_ui(app)
