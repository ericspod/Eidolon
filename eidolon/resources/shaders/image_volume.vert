#version 150
    
uniform mat4 p3d_ModelViewMatrix;
uniform mat4 p3d_ProjectionMatrix;

in vec4 p3d_Vertex;
in vec4 p3d_Color;

out vec4 vColor; 

void main() {
    float plane_index=p3d_Vertex.x;  // x value of the input vertex is the plane index for this point
    gl_Position = p3d_ModelViewMatrix * vec4(0.5, 0.5, 0.5, 1);  // position in the middle of the volume
    
    float scale = distance(p3d_ModelViewMatrix * vec4(1, 1, 1, 1), gl_Position);  // calculate bounding radius
    
    // move the point to its position on the line perpendicular with the camera's plane
    gl_Position.z += (plane_index * 2 * scale) - scale;
    gl_Position = p3d_ProjectionMatrix * gl_Position;
    
    vColor = p3d_Color;
}
