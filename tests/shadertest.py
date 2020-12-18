import sys
from PyQt5 import QtWidgets

import numpy as np

import eidolon.renderer
import eidolon.ui

from eidolon.mathdef import vec3, rotator, transform, generate_sphere, generate_axes_arrows, generate_line_cuboid

from panda3d.core import Shader

app = QtWidgets.QApplication(sys.argv)

win = eidolon.ui.SimpleApp(1200, 800)

verts, inds, norms, colors = generate_axes_arrows(5, 10)
axes = eidolon.renderer.SimpleFigure("axes", verts, inds, norms, colors)
axes.attach(win.cam)

bbverts, bbinds = generate_line_cuboid(vec3(10, 10, 10))
box = eidolon.renderer.SimpleFigure("box", bbverts, bbinds, colors=[(1, 1, 1, 1)] * len(bbverts))
box.attach(win.cam)



s = Shader.make(lang=Shader.SL_GLSL, geometry=geom_body, fragment=frag_body, vertex=vert_body)

num_items = 9

# verts = [(-1, 0, -1), (1, 0, -1), (-1, 0, 1), (1, 0, 1)]
verts = [(i, 0, 0) for i in range(num_items)]
inds = None  # [(0, 1, 2), (1, 3, 2)]
norms = None  # [(0, 0, 1)] * len(verts)
# colors = [
#     (1.0, 0.0, 0.0, 1.0),
#     (0.0, 1.0, 0.0, 1.0),
#     (0.0, 0.0, 1.0, 1.0),
#     (1.0, 1.0, 1.0, 0.0),
# ]
colors = [(1.0, 1.0, 1.0, 1.0)] * len(verts)

fig = eidolon.renderer.SimpleFigure("vol", verts, inds, norms, colors)
fig.attach(win.cam)

fig.scale=vec3.one*10

fig.camnodes[0].set_shader(s)
fig.camnodes[0].set_shader_input("vol_radius", box.aabb().radius)
fig.camnodes[0].set_shader_input("num_planes", num_items)


win.show()

eidolon.ui.exec_ui(app)
