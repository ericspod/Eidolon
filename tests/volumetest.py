import sys
from PyQt5 import QtWidgets

import numpy as np

import eidolon.renderer
import eidolon.ui

from eidolon.mathdef import vec3, rotator, transform, generate_sphere, generate_axes_arrows

from panda3d.core import Shader

app = QtWidgets.QApplication(sys.argv)

win = eidolon.ui.SimpleApp(1200, 800)

win.ctrl.set_position(vec3.one * 5)

sphere = generate_sphere(128, 128, 20, 1.2)

img = sphere[..., None].repeat(4, axis=3)

img[:, :5, :5, 0] = 1
img[:10, :, :10, 1] = 1
img[:15, :15, :, 2] = 1
img[..., 3] = 0.1 + (img.sum(axis=3) > 0).astype(np.float32)

# mesh = eidolon.renderer.ImagePlaneFigure("planes", img, True)
fig = eidolon.renderer.ImageVolumeFigure("planes", img)

fig.attach(win.cam)
fig.scale = vec3.one * 10

vert_body = """
    #version 130
    
    // Uniform inputs
    uniform mat4 p3d_ModelViewProjectionMatrix;
    
    // Vertex inputs
    in vec4 p3d_Vertex;
    in vec3 p3d_MultiTexCoord0;
    
    in int gl_VertexID;
    
    in float vol_radius;
    
    in int num_planes;
    
    // Output to fragment shader
    out vec3 texcoord;
    
    void main() {
        float plane_pos=vol_radius*(gl_VertexID-num_planes/2);
        gl_Position = p3d_ModelViewProjectionMatrix * (p3d_Vertex+vec4(float(plane_pos),0,0,0));
        texcoord = p3d_MultiTexCoord0;
    }
"""

geom_body = """
    #version 330 core
    
    uniform mat4 p3d_ModelViewProjectionMatrix;
    
    layout (points) in;
    layout (triangle_fan, max_vertices = 4) out;
    
    out vec3 fColor;  
    
    void main() {
        //fColor=gl_in[0].color;
        fColor=vec3(1.0,0.0,0.0);
        gl_Position = vec4(-100.0, -100.0, 0.0, 1.0); 
        EmitVertex();
    
        fColor=vec3(0.0,1.0,0.0);
        gl_Position =  vec4(100.0, -100.0, 0.0, 1.0);
        EmitVertex();
    
        fColor=vec3(0.0,0.0,1.0);
        gl_Position =  vec4(100.0, 100.0, 0.0, 1.0);
        EmitVertex();
    
        fColor=vec3(1.0,1.0,1.0);
        gl_Position =  vec4(-100.0, 100.0, 0.0, 1.0);
        EmitVertex();
        
        EndPrimitive();
    }
"""

geom_body = """
#version 330 core
layout (points) in;
layout (line_strip, max_vertices = 2) out;

void main() {    
    gl_Position = gl_in[0].gl_Position + vec4(-100., 0.0, 0.0, 0.0); 
    EmitVertex();

    gl_Position = gl_in[0].gl_Position + vec4( 100, 0.0, 0.0, 0.0);
    EmitVertex();
    
    EndPrimitive();
}
"""

frag_body = """
    #version 130
    
    uniform sampler3D p3d_Texture0;
    
    // Input from vertex shader
    in vec3 texcoord;
    in vec3 fColor;
    
    void main() {
      vec4 color = texture(p3d_Texture0, texcoord);
      gl_FragColor = color.rgba;
    }
"""

s = Shader.make(lang=Shader.SL_GLSL, geometry=geom_body, fragment=frag_body, vertex=vert_body)

fig.camnodes[0].set_shader(s)
fig.camnodes[0].set_shader_input("vol_radius", fig.aabb().radius)
fig.camnodes[0].set_shader_input("num_planes", fig.num_planes)

verts, inds, norms, colors = generate_axes_arrows(5, 10)
axes = eidolon.renderer.SimpleFigure("axes", verts, inds, norms, colors)
axes.attach(win.cam)

win.show()

eidolon.ui.qtrunner(app)
