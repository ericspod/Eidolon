import sys
from PyQt5 import QtWidgets

import numpy as np

import eidolon.renderer
import eidolon.ui

from eidolon.mathdef import vec3, rotator, transform, generate_sphere, generate_axes_arrows, generate_line_cuboid

win = eidolon.ui.SimpleApp(1200, 800)

win.ctrl.set_position(vec3.one * 5)

verts, inds, norms, colors = generate_axes_arrows(5, 10)
axes = eidolon.renderer.SimpleFigure("axes", verts, inds, norms, colors)
axes.attach(win.cam)

bbverts, bbinds = generate_line_cuboid(vec3(10, 10, 10))
box = eidolon.renderer.SimpleFigure("box", bbverts, bbinds, colors=[(1, 1, 1, 1)] * len(bbverts))
box.attach(win.cam)

sphere = generate_sphere(128, 128, 128, 1.2)

img = sphere[..., None].repeat(4, axis=3)

img[:, :5, :5, 0] = 1
img[:10, :, :10, 1] = 1
img[:15, :15, :, 2] = 1
img[..., 3] = (img.sum(axis=3) > 0).astype(np.float32)

fig = eidolon.renderer.ImageVolumeFigure("planes", img, num_planes=1000)

fig.attach(win.cam)
fig.scale = vec3.one * 10

win.run()
