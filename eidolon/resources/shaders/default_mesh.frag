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