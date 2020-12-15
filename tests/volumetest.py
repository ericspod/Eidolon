import sys
from PyQt5 import QtWidgets

import numpy as np

import eidolon.renderer
import eidolon.ui

from eidolon.mathdef import vec3, rotator, transform, generate_sphere, generate_axes_arrows

mgr = eidolon.renderer.Manager()
cam = eidolon.renderer.OffscreenCamera(mgr, "test", 400, 400)

ctrl = eidolon.ui.CameraController(cam, vec3.zero, 0, 0, 50)

# img = generate_sphere(128, 128, 20, 1.2)

img = np.zeros((128, 128, 20, 4), np.float32)

img[:, :5, :5, 0] = 1
img[:10, :, :10, 1] = 1
img[:15, :15, :, 2] = 1
img[..., 3] = 0.1 + (img.sum(axis=3) > 0).astype(np.float32)

mesh = eidolon.renderer.ImagePlaneMesh("planes", img, True)
mesh.attach(cam)
mesh.scale = vec3.one * 10

verts, inds, norms, colors = generate_axes_arrows(5, 10)

axes = eidolon.renderer.SimpleMesh("axes", verts, inds, norms, colors)
axes.attach(cam)

app = QtWidgets.QApplication(sys.argv)

camwidget = eidolon.ui.CameraWidget(mgr, cam)

ctrl.attach_events(camwidget.events)

appw = QtWidgets.QMainWindow()
appw.resize(800, 600)
appw.setCentralWidget(camwidget)
appw.show()

eidolon.ui.qtrunner(app)
