import numpy as np
from panda3d.core import Material

import eidolon.renderer
import eidolon.ui
from eidolon.mathdef import generate_axes_arrows, generate_center_sphere, generate_line_cuboid, rotator, transform, vec3

win = eidolon.ui.SimpleApp(1200, 800)

# win.cam.nodepath.setShaderAuto()

win.ctrl.position = vec3.one * 5

amb = eidolon.renderer.Light("amb", eidolon.renderer.LightType.AMBIENT, (0.3, 0.3, 0.3, 1))
amb.attach(win.cam)

light = eidolon.renderer.Light("dlight", eidolon.renderer.LightType.DIRECTIONAL, (0.3, 0.3, 0.3, 1))
light.attach(win.cam, True)

verts, inds, norms, colors = generate_axes_arrows(5, 10)
axes = eidolon.renderer.SimpleFigure("axes", verts, inds, norms, colors)
axes.attach(win.cam)

bbverts, bbinds = generate_line_cuboid(vec3(10, 10, 10))
box = eidolon.renderer.SimpleFigure("box", bbverts, bbinds, colors=[(1, 1, 1, 1)] * len(bbverts))
box.attach(win.cam)

bm = Material()
bm.set_emission((1, 1, 1, 1))
box.camnodes[0].set_material(bm)

sphere = generate_center_sphere(128, 128, 128, 1.2)

img = sphere[..., None].repeat(4, axis=3)

img[:, :5, :5, 0] = 1
img[:10, :, :10, 1] = 1
img[:15, :15, :, 2] = 1
img[..., 3] = (img.sum(axis=3) > 0).astype(np.float32)

fig = eidolon.renderer.ImageVolumeFigure("planes", img, num_planes=1000)

fig.attach(win.cam)
fig.scale = vec3.one * 10

# m=Material()
# m.set_specular((1, 1, 1, 1))
# fig.camnodes[0].set_material(m)

win.ctrl.set_camera_see_all()

win.exec()
