import sys
from PyQt5 import QtWidgets

import eidolon.renderer
import eidolon.ui

from eidolon.mathdef import vec3, generate_axes_arrows

from panda3d.core import Shader

app = QtWidgets.QApplication(sys.argv)

cam = eidolon.renderer.OffscreenCamera("test", 400, 400)

light = eidolon.renderer.Light("dlight", eidolon.renderer.LightType.DIRECTIONAL, (1, 1, 1, 1))
light.attach(cam, True)

amb = eidolon.renderer.Light("amb", eidolon.renderer.LightType.AMBIENT, (0.25, 0.25, 0.25, 1))
amb.attach(cam)

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

    in vec4 color;

    void main() {
        gl_FragColor=color;
    }
"""

# s = Shader.make(lang=Shader.SL_GLSL, vertex=vert_body, fragment=frag_body)

# cam.nodepath.setShader(s)

camwidget = eidolon.ui.CameraWidget(cam)

ctrl = eidolon.ui.CameraController(cam, vec3.zero, 0, 0, 50)
ctrl.attach_events(camwidget.events)

verts, inds, norms, colors = generate_axes_arrows(5, 10)

mesh = eidolon.renderer.SimpleFigure("axes", verts, inds, norms, colors)
mesh.attach(cam)

appw = QtWidgets.QMainWindow()
appw.resize(800, 600)
appw.setCentralWidget(camwidget)
appw.show()

eidolon.ui.exec_ui(app)
