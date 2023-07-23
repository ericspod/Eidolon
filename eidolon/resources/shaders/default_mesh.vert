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
