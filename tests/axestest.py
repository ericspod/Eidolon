import sys

from panda3d.core import Material
from PyQt5 import QtWidgets

import eidolon.renderer
import eidolon.ui
from eidolon.mathdef import generate_axes_arrows, vec3
from eidolon.scene import QtCamera3DController

win = eidolon.ui.SimpleApp(1200, 800)

# not using auto shaders if a shader is set
# win.cam.nodepath.setShaderAuto()

amb = eidolon.renderer.Light("amb", eidolon.renderer.LightType.AMBIENT, (0.1, 0.1, 0.1, 1))
amb.attach(win.cam)

light = eidolon.renderer.Light("dlight", eidolon.renderer.LightType.DIRECTIONAL, (0.5, 1.0, 0.5, 1))
light.attach(win.cam, True)

verts, inds, norms, colors = generate_axes_arrows(5, 10)
mesh = eidolon.renderer.SimpleFigure("axes", verts, inds, norms, colors)
mesh.attach(win.cam)

s = eidolon.renderer.shaders.make_shader_from_prefix("default_mesh")
mesh.set_shader(s)

m = Material()
# mesh.camnodes[0].set_material(m)

win.exec()
