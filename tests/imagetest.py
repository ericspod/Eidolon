import sys
from PyQt5 import QtWidgets

import eidolon.renderer
import eidolon.ui

from eidolon.mathdef import vec3, generate_plane, generate_axes_arrows
from eidolon.renderer import create_texture_np

import numpy as np

from panda3d.core import Texture

from scipy.misc import face

mgr = eidolon.renderer.RenderBase()
cam = eidolon.renderer.OffscreenCamera(mgr, "test", 400, 400)

ctrl = eidolon.ui.CameraController(cam, vec3.zero, 0, 0, 50)

verts, inds, norms, colors = generate_axes_arrows(5, 10)

axes = eidolon.renderer.SimpleFigure("axes", verts, inds, norms, colors)
axes.attach(cam)

verts = [(0, 0, 0), (10, 0, 0), (0, 10, 0), (10, 10, 0)]
inds = [(0, 1, 2), (1, 3, 2)]
norms = [(0, 0, 1)] * len(verts)
uvs = [(0, 0, 0), (1, 0, 0), (0, 1, 0), (1, 1, 0)]

# verts, inds, uvs = generate_plane(0)
# verts = [(v + vec3(0.5, 0.5, 0)) * 10 for v in verts]
# uvs=[v*vec3(2,1,0) for v in uvs]

# img=face().copy()
img = np.zeros((128, 150, 3), np.float32)

img[:, :20, 0] = 1
img[:30, :, 1] = 1
img[..., 2] = img.sum(axis=2) == 0

tex = create_texture_np(img)

mesh = eidolon.renderer.SimpleFigure("quad", verts, inds, None, None, uvs)
mesh.attach(cam)
mesh.set_texture(tex)

app = QtWidgets.QApplication(sys.argv)

camwidget = eidolon.ui.CameraWidget(mgr, cam)

ctrl.attach_events(camwidget.events)

appw = QtWidgets.QMainWindow()
appw.resize(800, 600)
appw.setCentralWidget(camwidget)
appw.show()

eidolon.ui.exec_ui(app)
