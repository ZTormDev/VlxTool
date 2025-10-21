#version 330 core
out vec4 f_color;

in vec3 v_tex_coords;

void main()
{
    // Colores para el gradiente
    vec3 top_color = vec3(0.5, 0.7, 1.0); // Azul claro
    vec3 bottom_color = vec3(0.1, 0.2, 0.4); // Azul oscuro

    // El interpolador 't' va de 0 (abajo) a 1 (arriba)
    // v_tex_coords.y va de -1 a 1, así que lo normalizamos al rango 0-1
    float t = (v_tex_coords.y + 1.0) / 2.0;

    // Mezclamos los colores basándonos en la altura
    f_color = vec4(mix(bottom_color, top_color, t), 1.0);
}