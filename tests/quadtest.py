import sys
from PyQt5 import QtWidgets

import eidolon.renderer
import eidolon.ui

from eidolon.mathdef import vec3


mgr = eidolon.renderer.RenderBase()
cam = eidolon.renderer.OffscreenCamera(mgr, "test", 400, 400)

ctrl = eidolon.rendere.QtCameraController(cam, vec3.zero, 0, 0, 50)

verts = [(0, 0, 0), (10, 0, 0), (0, 0, 10), (10, 0, 10)]
inds = [(0, 1, 2), (1, 3, 2)]
norms = [(0, 0, 1)] * len(verts)
colors = [
    (1.0, 0.0, 0.0, 1.0),
    (0.0, 1.0, 0.0, 1.0),
    (0.0, 0.0, 1.0, 1.0),
    (1.0, 1.0, 1.0, 0.0),
]

mesh = eidolon.renderer.SimpleFigure("quad", verts, inds, norms, colors)
mesh.attach(cam)

mesh.position = vec3(-5, -5, 0)

app = QtWidgets.QApplication(sys.argv)

camwidget = eidolon.ui.CameraWidget(mgr, cam)

ctrl.attach_events(camwidget.events)

appw = QtWidgets.QMainWindow()
appw.resize(800, 600)
appw.setCentralWidget(camwidget)
appw.show()

eidolon.ui.exec_ui(app)
