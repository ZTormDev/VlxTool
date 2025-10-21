// pivotGizmo.frag

#version 330 core

in vec3 v_color;
in vec3 v_local_pos; // NUEVO: Recibimos la posición local interpolada

out vec4 FragColor;

void main()
{
    // Las líneas van de una longitud de 0.0 en el centro a 0.5 en los extremos.
    // Calculamos una intensidad que es 1.0 en el centro y 0.0 en el extremo.
    float intensity = 1.0 - (length(v_local_pos) / 0.5);
    intensity = pow(intensity, 2.0); // Usamos pow() para que la caída del brillo sea más suave.

    // Definimos el color del núcleo brillante (blanco está bien).
    vec3 core_color = vec3(1.0, 1.0, 1.0);

    // Mezclamos el color del eje (v_color) con el color del núcleo (core_color)
    // usando la intensidad que calculamos.
    vec3 final_color = mix(v_color, core_color, intensity);

    FragColor = vec4(final_color, 1.0);
}