import sys
from PyQt5 import QtWidgets

import eidolon.renderer
import eidolon.ui
from eidolon.scene import QtCameraController

from eidolon.mathdef import vec3, generate_axes_arrows

from panda3d.core import Shader, Material

# app = QtWidgets.QApplication(sys.argv)

# cam = eidolon.renderer.OffscreenCamera("test", 400, 400)

win = eidolon.ui.SimpleApp(1200, 800)

win.cam.nodepath.setShaderAuto()

# amb = eidolon.renderer.Light("amb", eidolon.renderer.LightType.AMBIENT, (0, 1, 0, 1))
# amb.attach(win.cam)

light = eidolon.renderer.Light("dlight", eidolon.renderer.LightType.DIRECTIONAL, (0.5, 0.1, 0.5, 1))
light.attach(win.cam, True)

vert_body = """
    #version 150

    uniform mat4 p3d_ModelViewProjectionMatrix;
    uniform mat3 p3d_NormalMatrix;

    in vec4 p3d_Vertex;
    in vec4 p3d_Color;
    in vec3 p3d_Normal;
    in vec3 p3d_MultiTexCoord0;

    out vec4 color;
    out vec3 texcoord;
    out vec3 normal;
    out vec4 position;

    void main() {
        gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;

        color = p3d_Color;
        texcoord = p3d_MultiTexCoord0;
        normal = p3d_NormalMatrix* p3d_Normal;
        position=gl_Position;
    }
"""

frag_body = """
    #version 150

    uniform struct {
        vec4 ambient;
        vec4 diffuse;
        vec4 emission;
        vec3 specular;
        float shininess;

        // These properties are new in 1.10.
        vec4 baseColor;
        float roughness;
        float metallic;
        float refractiveIndex;
    } p3d_Material;

    uniform struct p3d_LightSourceParameters {
        // Primary light color.
        vec4 color;

        // Light color broken up into components, for compatibility with legacy
        // shaders.  These are now deprecated.
        vec4 ambient;
        vec4 diffuse;
        vec4 specular;

        // View-space position.  If w=0, this is a directional light, with the xyz
        // being -direction.
        vec4 position;

        // Spotlight-only settings
        vec3 spotDirection;
        float spotExponent;
        float spotCutoff;
        float spotCosCutoff;

        // Individual attenuation constants
        float constantAttenuation;
        float linearAttenuation;
        float quadraticAttenuation;

        // constant, linear, quadratic attenuation in one vector
        vec3 attenuation;

        // Shadow map for this light source
        sampler2DShadow shadowMap;

        // Transforms view-space coordinates to shadow map coordinates
        mat4 shadowViewMatrix;
    } p3d_LightSource[1];

    const int NUM_LIGHTS=1;
    
    in vec4 color;
    in vec3 normal;
    in vec4 position;

    vec4 compute_directional_light(vec3 ldir,vec3 norm, vec4 col){
        float mag=max(dot(ldir,norm),0);
        return col*mag;
    }

    void main() {
        vec4 col=length(color) > 0 ? color: p3d_Material.diffuse;

        gl_FragColor = p3d_Material.emission + col * p3d_Material.ambient;

        for(int n=0;n<NUM_LIGHTS;n++){
            vec4 lpos=p3d_LightSource[n].position;
            vec4 lcol=p3d_LightSource[n].color;

            if(lpos.w==0)
                gl_FragColor += col*compute_directional_light(lpos.xyz, normal, lcol);
        }
    }
"""

m=Material()
m.set_ambient((0.1, 0.1, 0.1, 1))

# s = Shader.make(lang=Shader.SL_GLSL, vertex=vert_body, fragment=frag_body)

s=eidolon.renderer.shaders.make_shader_from_prefix("default_mesh")

# cam.nodepath.setShader(s)

# camwidget = eidolon.ui.CameraWidget(cam)

# ctrl = QtCameraController(cam, vec3.zero, 0, 0, 50)
# ctrl.attach_events(camwidget.events)

verts, inds, norms, colors = generate_axes_arrows(5, 10)

mesh = eidolon.renderer.SimpleFigure("axes", verts, inds, norms, colors)
mesh.attach(win.cam)
mesh.set_shader(s)
mesh.camnodes[0].set_material(m)

# win.cam.nodepath.set_shader_input("ambient",1.0,0.0,1.0,1.0)

# appw = QtWidgets.QMainWindow()
# appw.resize(800, 600)
# appw.setCentralWidget(camwidget)
# appw.show()

# eidolon.ui.exec_ui(app)

win.exec()
