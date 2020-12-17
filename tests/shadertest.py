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

vert_body = """
    #version 150
    
    // Uniform inputs
    uniform mat4 p3d_ModelViewProjectionMatrix;
    uniform mat4 p3d_ModelViewMatrix;
    uniform mat4 p3d_ProjectionMatrix;

    // Vertex inputs
    in vec4 p3d_Vertex;
    in vec4 p3d_Color;
    
    //in int gl_VertexID;
    
    uniform float vol_radius;
    
    uniform int num_planes;
    
    // Output to fragment shader
    out vec4 vColor; 
    
    void main() {
        int p2=num_planes/2;
        int idx=int(p3d_Vertex.x);
        //float z=(idx-p2)*(vol_radius/p2);
        //float z=p3d_Vertex.x;
        //float z=idx-p2;
        
        float z=((p3d_Vertex.x*0.5)/num_planes)-1;
        
        //gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;
        gl_Position = p3d_ModelViewProjectionMatrix * vec4(0.5,0.5,0.5,1);
        gl_Position.z+=z;
        vColor=vec4(float(idx)/num_planes,1,0,1.0); //p3d_Color;
    }
"""

geom_body = """
    #version 150 core
    
    layout(points) in;
    layout(line_strip, max_vertices = 7) out;
    
    uniform mat4 p3d_ModelViewProjectionMatrix;
    uniform mat4 p3d_ModelViewMatrix;
    uniform mat4 p3d_ProjectionMatrix;
    
    in vec4 vColor[]; // Output from vertex shader for each vertex
    
    out vec4 fColor; // Output to fragment shader

    int[24] edges={0, 1, 0, 2, 1, 3, 2, 3, 0, 4, 1, 5, 2, 6, 3, 7, 4, 5, 4, 6, 5, 7, 6, 7};

    vec4 v4lerp(float val, vec4 v1, vec4 v2)
    {
        return (1.0-val)*v1+val*v2;
    }
    
    void main()
    {
        float z=gl_in[0].gl_Position.z;
        
        vec4 corners[]={
            p3d_ModelViewProjectionMatrix*vec4(0,0,0,1),
            p3d_ModelViewProjectionMatrix*vec4(1,0,0,1),
            p3d_ModelViewProjectionMatrix*vec4(0,1,0,1),
            p3d_ModelViewProjectionMatrix*vec4(1,1,0,1),
            p3d_ModelViewProjectionMatrix*vec4(0,0,1,1),
            p3d_ModelViewProjectionMatrix*vec4(1,0,1,1),
            p3d_ModelViewProjectionMatrix*vec4(0,1,1,1),
            p3d_ModelViewProjectionMatrix*vec4(1,1,1,1)
        };
        
        fColor = vColor[0]; // Point has only one vertex
        
        for(int i=0;i<24;i+=2){
            vec4 v1=corners[edges[i]];
            vec4 v2=corners[edges[i+1]];
            float z1=v1.z-z;
            float z2=v2.z-z;
            
            if( (z1<0 && z2>=0) || (z1>=0 && z2<0)){
                float v=abs(z1)/(abs(z1)+abs(z2));
                
                gl_Position=v4lerp(v,v1,v2);
                EmitVertex();
            } 
        }
        
        /*
        gl_Position = gl_in[0].gl_Position+vec4(-1,-1,0,0);
        EmitVertex();
    
        gl_Position = gl_in[0].gl_Position+vec4(1,-1,0,0);
        EmitVertex();
    
        gl_Position = gl_in[0].gl_Position+vec4(1,1,0,0);
        EmitVertex();
        
        gl_Position = gl_in[0].gl_Position+vec4(-1,1,0,0);
        EmitVertex();
        
        gl_Position = gl_in[0].gl_Position+vec4(-1,-1,0,0);
        EmitVertex();
        */
        
        EndPrimitive();
    }
"""

frag_body = """
    #version 150
    
    //uniform sampler3D p3d_Texture0;
    
    // Input from vertex shader
    //in vec3 texcoord;
    in vec4 fColor;
    
    void main() {
      //vec4 color = texture(p3d_Texture0, texcoord);
      gl_FragColor = fColor.rgba;
    }
"""

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

eidolon.ui.qtrunner(app)
