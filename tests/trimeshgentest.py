import sys

import numpy as np

from PyQt5 import QtWidgets

import eidolon.renderer
import eidolon.ui

from eidolon.mathdef import vec3, Mesh, ElemType, calculate_tri_mesh, calculate_mesh_ext_adj, generate_tri_normals

cam = eidolon.renderer.OffscreenCamera("test", 400, 400)

ctrl = eidolon.ui.CameraController(cam, vec3.zero, 0, 0, 50)

# dat = np.load("data/linmesh.npz")
# mesh = Mesh(dat["x"], [("inds", dat["t"]-1, ElemType._Hex1NL)])

nodes = np.array(list(np.ndindex(2, 2, 2)))[:, ::-1]
nodes = np.append(nodes, nodes + [(1, 0, 0)], axis=0)

nodes = np.array([
    [0, 0, 0],
    [1, 0, 0],
    [0, 1, 0],
    [1, 1, 0],
    [0, 0, 1],
    [1, 0, 1],
    [0, 1, 1],
    [1, 1, 1],
    [2, 0, 0],
    [2, 1, 0],
    [2, 0, 1],
    [2, 1, 1],
    [3, 0, 0],
    [3, 1, 0],
    [3, 0, 1],
    [3, 1, 1],
    [0, 0, 2],
    [1, 0, 2],
    [0, 1, 2],
    [1, 1, 2]
], dtype=np.float32)

inds = np.array([
    (0, 1, 2, 3, 4, 5, 6, 7),
    (1, 8, 3, 9, 5, 10, 7, 11),
    (8, 12, 9, 13, 10, 14, 11, 15),
    (4, 5, 6, 7, 16, 17, 18, 19)
], dtype=np.int32)

mesh = Mesh(nodes, {"inds": (inds, ElemType._Hex1NL)})

tri_mesh = calculate_tri_mesh(mesh, 0, "inds", external_only=True)
norms = generate_tri_normals(tri_mesh.nodes, tri_mesh.topos["inds"][0])

fig = eidolon.renderer.SimpleFigure("axes", tri_mesh.nodes, tri_mesh.topos["inds"][0], norms)
fig.attach(cam)

fig.scale = vec3.one * 10
# fig.camnodes[0].set_render_mode_wireframe()

app = QtWidgets.QApplication(sys.argv)

camwidget = eidolon.ui.CameraWidget(cam)

ctrl.attach_events(camwidget.events)

ctrl.move_see_all()

light = eidolon.renderer.Light("dlight", eidolon.renderer.LightType.DIRECTIONAL, (1, 1, 1, 1))
light.attach(cam, True)

amb = eidolon.renderer.Light("amb", eidolon.renderer.LightType.AMBIENT, (0.25, 0.25, 0.25, 1))
amb.attach(cam)

appw = QtWidgets.QMainWindow()
appw.resize(800, 600)
appw.setCentralWidget(camwidget)
appw.show()

eidolon.ui.exec_ui(app)
