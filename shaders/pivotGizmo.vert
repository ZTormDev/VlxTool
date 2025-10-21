// pivotGizmo.vert

#version 330 core

layout (location = 0) in vec3 a_pos;
layout (location = 1) in vec3 a_color;

uniform mat4 model;
uniform mat4 view;
uniform mat4 projection;

out vec3 v_color;
out vec3 v_local_pos;

void main()
{
    gl_Position = projection * view * model * vec4(a_pos, 1.0);

    // --- LA LÍNEA CORREGIDA ---
    // Un valor Z negativo en NDC está MÁS CERCA de la cámara.
    gl_Position.z = -gl_Position.w * 0.9999;

    v_color = a_color;
    v_local_pos = a_pos;
}