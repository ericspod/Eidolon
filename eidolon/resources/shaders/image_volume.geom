#version 150 core

layout(points) in;
layout(triangle_strip, max_vertices = 12) out; // max of 4 triangles with 3 vertices

uniform mat4 p3d_ModelViewProjectionMatrix;

in vec4 vColor[]; 

out vec4 fColor;
out vec3 texcoord;
out vec3 texnorm;

// topos of the edges for the cube, each successive pair represents one edge
const int[24] edges=int[24](  
    0, 1, 0, 2, 1, 3, 2, 3, // bottom square 
    0, 4, 1, 5, 2, 6, 3, 7, // vertical edges 
    4, 5, 4, 6, 5, 7, 6, 7 // top square
);

// topos of the triangles defining this plane, up to 4 depending on how many vertices are generated
const int[12] triangle_indices = int[12]( 0, 1, 2, 0, 2, 3, 0, 3, 4, 0, 4, 5 );

// vertices for the unit cude, also used as texture uvw coordinates 
const vec4[8] unitcube=vec4[8]( 
    vec4(0,0,0,1), vec4(1,0,0,1), vec4(0,1,0,1), vec4(1,1,0,1), 
    vec4(0,0,1,1), vec4(1,0,1,1), vec4(0,1,1,1), vec4(1,1,1,1)
);

// linear interpolation between vec4 values
vec4 v4lerp(float val, vec4 v1, vec4 v2) { return (1.0-val)*v1+val*v2; }

// Determine the polygon which represents the intersection of the plane at distance z from the camera by finding every
// edge bisected by the plane and taking the intersection point as a vertex of the output triangle strip.
void main()
{
    fColor = vColor[0];  // use the same color for all vertices
    float z = gl_in[0].gl_Position.z;  // distance from the camera of this plane
    vec4[8] corners;  // projected corners of the image volume
    vec4[6] vertices;  // up to 6 vertices are generated for this plane
    vec3[6] texcoords; // texture coordinates for vertices
    float[6] angles;  // angle of each vertex around the camera axis, used for sorting in circular order
    int num_vertices=0;  // number of generated vertices, from 3 to 6
    
    // project all of the corners of the volume into camera space
    for(int i=0;i<8;i++)
        corners[i]=p3d_ModelViewProjectionMatrix*unitcube[i];
        
    vec4 center=p3d_ModelViewProjectionMatrix*vec4(0.5,0.5,0.5,1);  // center of volume

    // Consider each edge of the volume, if one vertex is below the plane and other above then the edge bisects the
    // plane at a point on that edge. This position is stored as a vertex, which happens between 3 and 6 times.         
    for(int i=0;i<24;i+=2){
        vec4 v1=corners[edges[i]];
        vec4 v2=corners[edges[i+1]];
        float z1=v1.z-z;  // vertex heights from plane
        float z2=v2.z-z;
        
        // if one of the vertices is below the plane and one above then a vertex is found on the edge
        if( (z1 < 0 && z2 >= 0) || (z1 >= 0 && z2 < 0)){
            // vertex heights from the plane are used to determine interpolation value xi to get the intersect point
            float xi = abs(z1) / (abs(z1) + abs(z2));  
            vec4 vertex = v4lerp(xi, v1, v2);  // intersection point on the edge
            vec3 tcoord = v4lerp(xi, unitcube[edges[i]], unitcube[edges[i + 1]]).xyz;  // interpolate texture coords
            
            // store the vertex, texture coordinate, and its angle at the bottom of the list
            vertices[num_vertices] = vertex;
            texcoords[num_vertices] = tcoord;
            angles[num_vertices] = atan(vertex.y-center.y,vertex.x-center.x);
            
            // move the new vertex up to its sorted position in the list, this ensures a circular sort order
            for(int idx=num_vertices; idx>0 && angles[idx]<angles[idx-1];idx--){
                vec4 vtemp=vertices[idx-1];
                float atemp=angles[idx-1];
                vec3 ttemp=texcoords[idx-1];
                
                vertices[idx-1]=vertices[idx];
                angles[idx-1]=angles[idx];
                texcoords[idx-1]=texcoords[idx];
                
                vertices[idx]=vtemp;
                angles[idx]=atemp;
                texcoords[idx]=ttemp;
            }
            
            num_vertices++;
        } 
    }

    texnorm=cross(texcoords[1]-texcoords[0],texcoords[2]-texcoords[0]); // normal of the plane in texture space
    
    // iterate over every triangle index, ending the primitive once a triangle is emitted
    for(int i=0;i<3*(num_vertices-2);i++){
        int idx=triangle_indices[i];
        gl_Position=vertices[idx];
        texcoord=texcoords[idx];
        EmitVertex();
        
        if(i%3==2)  // draw each triangle separately
            EndPrimitive();
    }
}