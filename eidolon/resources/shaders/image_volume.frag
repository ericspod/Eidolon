#version 150
    
// The sum of all active ambient light colors.
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

const float TRANS_DIST=0.001;
const float TRANS_THRESHOLD=0.01;

// uniform mat4 p3d_ModelViewProjectionMatrix;
// uniform mat3 p3d_NormalMatrix;
// uniform mat4 p3d_ProjectionMatrixInverse;

uniform sampler3D p3d_Texture0;
uniform float alpha;

in vec3 texcoord;
in vec3 texnorm;
out vec4 fragcolor;

vec4 calculate_directional_light(vec3 ldir, vec3 norm, vec4 diffuse, vec3 specular, float shininess){
    ldir = normalize(ldir);
    vec3 halfdir = normalize(ldir + vec3(0, 0, 1)); // assumes eye direction is (0,0,1)

    float mag = clamp(dot(ldir, norm), 0, 1);
    float smag = clamp(dot(halfdir, norm), 0, 1);
    float power = pow(smag, shininess);
    return (diffuse * mag) + vec4(specular * power, 1.0);
}

void main() {
    // fragcolor=vec4(abs(normalize(texnorm)),1.0);

    // vec4 tdir=(p3d_ProjectionMatrixInverse*vec4(0,0,1,1))-(p3d_ProjectionMatrixInverse*vec4(0,0,0,1));
    // vec3 tnorm=normalize(tdir.xyz/tdir.w);
    // fragcolor=vec4(tnorm,1.0);

    // vec4 ncolor=texture(p3d_Texture0, texcoord+tnorm);
    // if(ncolor.a<=TRANS_THRESHOLD)
        // fragcolor.r=1.0;

    // ORIGINAL
    // fragcolor = texture(p3d_Texture0, texcoord);
    // fragcolor.a = alpha;

    fragcolor=vec4(1.0,0,0,0.01);

    // fragcolor=vec4(0);
    // col=p3d_Material.emission + p3d_LightModel.ambient * p3d_Material.ambient;

    // for(int n=0;n<NUM_LIGHTS;n++){
    //     vec4 lpos=p3d_LightSource[n].position;
    //     vec4 lcol=p3d_LightSource[n].color;

    //     if(lpos.w==0)
    //         fragcolor += col*compute_directional_light(lpos.xyz, normal, lcol);
    // }

    // fragcolor *= texture(p3d_Texture0, texcoord);
}