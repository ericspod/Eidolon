import sys

import numpy as np

from PyQt5 import QtWidgets

import eidolon.renderer
import eidolon.ui

from eidolon.mathdef import vec3, Mesh, ElemType, calculate_tri_mesh, calculate_field, calculate_field_colors

cam = eidolon.renderer.OffscreenCamera("test", 400, 400)

ctrl = eidolon.ui.CameraController(cam, vec3.zero, 0, 0, 50)

dat = np.load("data/linmesh.npz")
# dat = np.load("data/cuboid.npz")

mesh = Mesh(dat["x"], {"inds": (dat["t"] - 1, ElemType._Hex1NL)}, {"field": (dat["d"], "inds")})

# nodes = np.array([
#     [0, 0, 0],
#     [1, 0, 0],
#     [0, 1, 0],
#     [1, 1, 0],
#     [0, 0, 1],
#     [1, 0, 1],
#     [0, 1, 1],
#     [1, 1, 1],
#     [2, 0, 0],
#     [2, 1, 0],
#     [2, 0, 1],
#     [2, 1, 1],
#     [3, 0, 0],
#     [3, 1, 0],
#     [3, 0, 1],
#     [3, 1, 1],
#     [0, 0, 2],
#     [1, 0, 2],
#     [0, 1, 2],
#     [1, 1, 2]
# ], dtype=np.float32)
#
# inds = np.array([
#     (0, 1, 2, 3, 4, 5, 6, 7),
#     (1, 8, 3, 9, 5, 10, 7, 11),
#     (16, 17, 18, 19, 4, 5, 6, 7),  # (4, 5, 6, 7, 16, 17, 18, 19)
#     (8, 12, 9, 13, 10, 14, 11, 15),
# ], dtype=np.int32)
#
# mesh = Mesh(nodes, {"inds": (inds, ElemType._Hex1NL)})

print(mesh.nodes.shape, mesh.topos["inds"][0].shape)

tri_mesh = calculate_tri_mesh(mesh, 0, "inds", external_only=True, octree_threshold=100000000)
field = calculate_field(tri_mesh, "field")
colors = calculate_field_colors(tri_mesh, "field", lambda i: (i, 0, 1 - i, 1))

norms = tri_mesh.other_data["norms"]
colors = tri_mesh.other_data["colors"]

fig = eidolon.renderer.SimpleFigure("trimesh", tri_mesh.nodes, tri_mesh.topos["inds"][0], norms, colors)
fig.attach(cam)

fig.set_render_mode(eidolon.renderer.RenderMode.FILLED_WIREFRAME)

app = QtWidgets.QApplication(sys.argv)

camwidget = eidolon.ui.CameraWidget(cam)

ctrl.attach_events(camwidget.events)

ctrl.set_camera_see_all()

light = eidolon.renderer.Light("dlight", eidolon.renderer.LightType.DIRECTIONAL, (0.5, 0.5, 0.5, 1))
light.attach(cam, True)

amb = eidolon.renderer.Light("amb", eidolon.renderer.LightType.AMBIENT, (0.25, 0.25, 0.25, 1))
amb.attach(cam)

appw = QtWidgets.QMainWindow()
appw.resize(800, 600)
appw.setCentralWidget(camwidget)
appw.show()

eidolon.ui.exec_ui(app)

