#version 150

uniform struct p4d_MaterialParameters {
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

// The sum of all active ambient light colors.
uniform struct p3d_LightModelParameters {
  vec4 ambient;
} p3d_LightModel;

const int NUM_LIGHTS=10;

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
} p3d_LightSource[NUM_LIGHTS];

uniform mat4 p3d_ModelViewProjectionMatrix;
uniform mat4 p3d_ModelViewProjectionMatrixInverse;
uniform mat3 p3d_NormalMatrixInverse;

in vec4 color;
in vec3 normal;
in vec4 position;

// in vec4 p3d_Vertex;

uniform vec3 landmark;
uniform float angle;

out vec4 frag_color;

vec4 calculate_directional_light(vec3 ldir, vec3 norm, vec4 diffuse, vec3 specular, float shininess){
    ldir = normalize(ldir);
    vec3 halfdir = normalize(ldir + vec3(0, 0, 1)); // assumes eye direction is (0,0,1)

    float mag = clamp(dot(ldir, norm), 0, 1);
    float smag = clamp(dot(halfdir, norm), 0, 1);
    float power = pow(smag, shininess);
    return (diffuse * mag) + vec4(specular * power, 1.0);
}

float calculate_falloff(float dist, float constant, float linear, float quadratic){
    return 1.0 / (constant + linear * dist + quadratic * dist * dist);
}

void main() {
    frag_color=p3d_LightModel.ambient * p3d_Material.ambient;

    for(int n=0;n<NUM_LIGHTS;n++){
        vec4 lpos=p3d_LightSource[n].position;
        vec3 sdir=p3d_LightSource[n].spotDirection;
        vec4 lcol=p3d_LightSource[n].color;
        
        if(lpos.w==0){
            frag_color += calculate_directional_light(
                lpos.xyz, normal, lcol * p3d_Material.diffuse, p3d_Material.specular * lcol.rgb, p3d_Material.shininess
            );
        }
        // // TODO: point and spot lights
        // else {//if(length(ldir)==0){
        //     vec3 ldir=lpos.xyz-position.xyz*lpos.w;
        //     vec4 spot_col = calculate_directional_light(
        //         normalize(ldir), normal, lcol * p3d_Material.diffuse, p3d_Material.specular * lcol.rgb, p3d_Material.shininess
        //     );
        //     // vec3 atten_vec=p3d_LightSource[n].attenuation;
        //     // float atten=calculate_falloff(length(lpos.xyz-position.xyz),atten_vec.x,atten_vec.y,atten_vec.z);
        //     frag_color += spot_col ;//* atten;
        // }
    }

    // vertex color
    if(length(color)>0)
        frag_color *= color;  // TODO: texture color instead of vertex color if present

    frag_color += p3d_Material.emission;

    vec4 lm=p3d_ModelViewProjectionMatrix*vec4(landmark, 1);
    vec3 axis=normalize(-lm.xyz);
    vec3 to_vert=normalize(position.xyz-lm.xyz);

    // frag_color.r=length(position.xyz)*0.001;
    // frag_color.g=frag_color.b=frag_color.a=1.0;

    float v_angle = acos(dot(axis,to_vert));

    if(v_angle<angle)
        frag_color.a=0;
    else if((v_angle-angle)<0.01)
        frag_color.rgba=vec4(0,0,0,1);

    // float lm_angle=(1.0-dot(axis,to_vert))*pi*0.5;
    // if(lm_angle<angle)
        // frag_color.r=1;

}