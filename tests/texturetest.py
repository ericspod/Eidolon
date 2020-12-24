import sys
from PyQt5 import QtWidgets

import eidolon.renderer
import eidolon.ui

from eidolon.mathdef import vec3, rotator, transform, generate_circle
from eidolon.renderer import create_texture_np

mgr = eidolon.renderer.RenderBase()
cam = eidolon.renderer.OffscreenCamera(mgr, "test", 400, 400)

ctrl = eidolon.ui.CameraController(cam, vec3.zero, 0, 0, 50)

verts = [(0, 0, 0), (10, 0, 0), (0, 0, 10), (10, 0, 10)]
inds = [(0, 1, 2), (1, 3, 2)]
norms = [(0, 0, 1)] * len(verts)
colors = [
    (1.0, 0.0, 0.0, 1.0),
    (0.0, 1.0, 0.0, 1.0),
    (0.0, 0.0, 1.0, 1.0),
    (1.0, 1.0, 1.0, 0.0),
]
uvs = [(0, 0, 0), (1, 0, 0), (0, 1, 0), (1, 1, 0)]

circle_img = generate_circle(128, 128, 0.8)[:, :, None].repeat(2, 2)

tex = create_texture_np(circle_img)

mesh = eidolon.renderer.SimpleFigure("quad", verts, inds, norms, colors, uvs)
mesh.attach(cam)
mesh.position = vec3(-5, -5, 0)
mesh.orientation = rotator.from_axis(vec3.X, 0.3)
mesh.scale = vec3(1.5, 1, 0.9)
mesh.set_texture(tex)

app = QtWidgets.QApplication(sys.argv)

camwidget = eidolon.ui.CameraWidget(mgr, cam)

ctrl.attach_events(camwidget.events)

appw = QtWidgets.QMainWindow()
appw.resize(800, 600)
appw.setCentralWidget(camwidget)
appw.show()

eidolon.ui.exec_ui(app)
