import sys
from PyQt5 import QtWidgets

import eidolon.renderer
import eidolon.ui

from eidolon.mathdef import vec3, generate_sphere, generate_tri_normals,generate_separate_tri_mesh,generate_axes_arrows

from panda3d.core import Material

win = eidolon.ui.SimpleApp(1200, 800)

# not using auto shaders if a shader is set
# win.cam.nodepath.setShaderAuto()

amb = eidolon.renderer.Light("amb", eidolon.renderer.LightType.AMBIENT, (0.3, 0.3, 0.3, 1))
amb.attach(win.cam)

light = eidolon.renderer.Light("dlight", eidolon.renderer.LightType.DIRECTIONAL, (0.3, 0.6, 0.3, 1))
light.attach(win.cam, True)

verts, inds = generate_sphere(2)
verts, inds = generate_separate_tri_mesh(verts,inds)
norms = generate_tri_normals(verts, inds)
colors = [(1, 1, 1, 1)] * len(verts)

auto_mesh = eidolon.renderer.SimpleFigure("auto_mesh", verts, inds, norms, colors)
auto_mesh.attach(win.cam)
auto_mesh.camnodes[0].set_shader_auto()
auto_mesh.position=vec3(-20,0,0)
auto_mesh.scale=vec3(10,10,10)

shader_mesh = eidolon.renderer.SimpleFigure("shader_mesh", verts, inds, norms, colors)
shader_mesh.attach(win.cam)
shader_mesh.position=vec3(20,0,0)
shader_mesh.scale=vec3(10,10,10)
# shader_mesh.camnodes[0].set_shader_auto()

verts, inds, norms, colors = generate_axes_arrows(5, 10)
axes = eidolon.renderer.SimpleFigure("axes", verts, inds, norms, colors)
axes.attach(win.cam)
axes.camnodes[0].set_shader_auto()


shader_mesh.set_shader(eidolon.renderer.shaders.make_shader_from_prefix("default_mesh"))

m=Material()
m.set_diffuse((1,1,0,1.0))
# m.set_specular((1,0,0,1))
# m.set_emission((0,0,0.25,1))
# m.shininess=64
auto_mesh.camnodes[0].set_material(m)
shader_mesh.camnodes[0].set_material(m)

win.ctrl.set_camera_see_all()

win.exec()
