import sys
from PyQt5 import QtWidgets

import eidolon.renderer
import eidolon.ui

from eidolon.mathdef import vec3
from eidolon.renderer import create_texture_np

from scipy.misc import face

mgr = eidolon.renderer.Manager()
cam = eidolon.renderer.OffscreenCamera(mgr, "test", 400, 400)

ctrl = eidolon.ui.CameraController(cam, vec3.zero, 0, 0, 50)

verts = [(-10, 0, -10), (10, 0, -10), (-10, 0, 10), (10, 0, 10)]
inds = [(0, 1, 2), (1, 3, 2)]
norms = [(0, 0, 1)] * len(verts)
uvs = [(0, 1), (1, 1), (0, 0), (1, 0)]

tex = create_texture_np(face())

mesh = eidolon.renderer.SimpleMesh("quad", verts, inds, norms, None, uvs)
mesh.attach(cam)
mesh.set_texture(tex)

app = QtWidgets.QApplication(sys.argv)

camwidget = eidolon.ui.CameraWidget(mgr, cam)

ctrl.attach_events(camwidget.events)

appw = QtWidgets.QMainWindow()
appw.resize(800, 600)
appw.setCentralWidget(camwidget)
appw.show()

eidolon.ui.qtrunner(app)
