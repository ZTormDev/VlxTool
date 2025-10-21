#version 330 core

flat in uint v_block_type; // Este nombre ahora coincide con el del vertex shader
in vec3 f_normal;
in float f_ao;

out vec4 f_color;

#define MAX_BLOCK_TYPES 16u

uniform vec3 u_block_palette[MAX_BLOCK_TYPES];

uniform vec3 u_sun_direction;
uniform vec3 u_sun_color;

void main()
{
    if (v_block_type >= MAX_BLOCK_TYPES) {
        f_color = vec4(1.0, 0.0, 1.0, 1.0); // Color de error
        return;
    }

    vec3 object_color = u_block_palette[v_block_type];
    
    vec3 norm = normalize(f_normal);
    vec3 ambient = vec3(0.3, 0.4, 0.5);
    float diff = max(dot(norm, -u_sun_direction), 0.0);
    vec3 diffuse = diff * u_sun_color;
    
    vec3 final_lighting = (ambient + diffuse) * object_color * f_ao;
    
    f_color = vec4(final_lighting, 1.0);
}