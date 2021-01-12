import sys
from PyQt5 import QtWidgets

import numpy as np
from scipy.ndimage import gaussian_filter

import eidolon.renderer
import eidolon.ui

from eidolon.mathdef import vec3, rotator, transform, generate_center_circle, generate_axes_arrows
from eidolon.renderer import create_texture_np

from panda3d.core import Shader, TextureStage

app = QtWidgets.QApplication(sys.argv)

win = eidolon.ui.SimpleApp(1200, 800)

verts, inds, norms, colors = generate_axes_arrows(5, 10)
axes = eidolon.renderer.SimpleFigure("axes", verts, inds, norms, colors)
axes.attach(win.cam)

# img = np.zeros((128, 150, 3), np.float32)
#
# img[:, :20, 0] = 1
# img[:30, :, 1] = 1
# img[..., 2] = img.sum(axis=2) == 0

img = generate_center_circle(128, 128, 0.8)  # [:, :, None].repeat(2, 2)
img = gaussian_filter(img, 6).astype(np.float32)

tex = create_texture_np(img)

spectrum = np.zeros((64, 64, 4), np.float32)
spectrum[..., 0] = np.linspace(0, 1, 64)[::-1, None].repeat(64, axis=1)
spectrum[..., 2] = np.linspace(0, 1, 64)[:, None].repeat(64, axis=1)
spectrum[..., 3] = np.linspace(0, 1, 64)[None, ::-1].repeat(64, axis=0)

# spectrum = np.linspace(0, 1, 64).astype(np.float32)
# spectrum = spectrum[:, None].repeat(2, axis=1)

tspectrum = create_texture_np(spectrum)

vert_body = """
    #version 150

    uniform mat4 p3d_ModelViewProjectionMatrix;

    in vec4 p3d_Vertex;
    in vec4 p3d_Color;
    in vec3 p3d_MultiTexCoord0;

    out vec4 color;
    out vec3 texcoord;

    void main() {
        gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;

        color = p3d_Color;
        texcoord=p3d_MultiTexCoord0;
    }
"""

frag_body = """
    #version 150

    uniform sampler2D p3d_Texture0;
    uniform sampler2D p3d_Texture1;

    in vec3 texcoord;
    in vec4 color;
    
    void main() {
        //gl_FragColor=color;
        vec4 texcolor = texture(p3d_Texture0, texcoord.xy);
        float mag=length(texcolor.rgb);
         
        gl_FragColor = texture(p3d_Texture1, vec2(mag,mag));
    }
"""

s = Shader.make(lang=Shader.SL_GLSL, vertex=vert_body, fragment=frag_body)

num_items = 9

verts = [(-10, 0, -10), (10, 0, -10), (-10, 0, 10), (10, 0, 10)]
inds = [(0, 1, 2), (1, 3, 2)]
norms = [(0, -1, 0)] * len(verts)
colors = [
    (1.0, 0.0, 0.0, 1.0),
    (0.0, 1.0, 0.0, 1.0),
    (0.0, 0.0, 1.0, 1.0),
    (1.0, 1.0, 1.0, 0.0),
]
texcoords = [(0, 0, 0), (1, 0, 0), (0, 1, 0), (1, 1, 0)]

fig = eidolon.renderer.SimpleFigure("quad", verts, inds, norms, colors, texcoords)
fig.attach(win.cam)

fig.camnodes[0].set_texture(TextureStage("ts"), tex)
fig.camnodes[0].set_texture(TextureStage("spec"), tspectrum)
fig.camnodes[0].set_shader(s)
# fig.camnodes[0].set_shader_input("vol_radius", box.aabb().radius)
# fig.camnodes[0].set_shader_input("num_planes", num_items)


win.show()

eidolon.ui.exec_ui(app)
