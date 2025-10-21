#version 330 core

layout (location = 0) in vec3 a_pos;
layout (location = 1) in vec3 a_normal;
layout (location = 2) in uint a_block_type;
layout (location = 3) in float a_ao;

uniform mat4 model;
uniform mat4 view;
uniform mat4 projection;

flat out uint v_block_type;
out vec3 f_normal;
out float f_ao;

void main()
{
    gl_Position = projection * view * model * vec4(a_pos, 1.0);
    f_normal = mat3(transpose(inverse(model))) * a_normal;
    v_block_type = a_block_type;
    f_ao = a_ao;
}