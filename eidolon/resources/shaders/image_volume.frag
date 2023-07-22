#version 150
    
uniform sampler3D p3d_Texture0;
uniform float alpha;

in vec3 texcoord;
out vec4 fragcolor;

void main() {
    fragcolor = texture(p3d_Texture0, texcoord);
    fragcolor.a *= alpha;
}