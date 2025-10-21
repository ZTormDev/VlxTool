# src/Config.py
import os
import numpy as np
from OpenGL.GL import (
    glCreateShader, glShaderSource, glCompileShader, glGetShaderiv, GL_COMPILE_STATUS,
    glGetShaderInfoLog, glDeleteShader, glCreateProgram, glAttachShader, glLinkProgram,
    glGetProgramiv, GL_LINK_STATUS, glGetProgramInfoLog, glDeleteProgram
)
from OpenGL.GL import GL_VERTEX_SHADER, GL_FRAGMENT_SHADER, GL_FALSE

# --- Screen Dimensions ---
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720

# --- Vertex Data Type ---
# Define el layout de la memoria para un solo vértice.
# Esto debe coincidir exactamente con los atributos definidos en Mesh.py y leídos en el vertex shader.
# 'f4' es un float de 4 bytes (32-bit). '(3,)f4' es un array de 3 floats.
# 'u4' es un unsigned int de 4 bytes (32-bit).
data_type_vertex = np.dtype([
    ('position', '(3,)f4'),   # Coordenadas X, Y, Z (12 bytes)
    ('normal',   '(3,)f4'),   # Normales X, Y, Z   (12 bytes)
    ('block_id', 'u4'),       # ID del bloque        (4 bytes)
    ('ao',       'f4')        # Oclusión ambiental   (4 bytes)
    # Total por vértice = 32 bytes
])


def create_shader_program(vertex_filepath, fragment_filepath):
    """
    Compila y enlaza los shaders de vértice y fragmento.
    Devuelve el ID del programa del shader, o 0 si ocurre un error.
    """
    try:
        with open(vertex_filepath, 'r') as f:
            vertex_src = f.read()
        with open(fragment_filepath, 'r') as f:
            fragment_src = f.read()
    except FileNotFoundError as e:
        print(f"Error: No se pudo encontrar el archivo del shader. {e}")
        return 0

    # Compilar Vertex Shader
    vertex_shader = glCreateShader(GL_VERTEX_SHADER)
    glShaderSource(vertex_shader, vertex_src)
    glCompileShader(vertex_shader)
    if not glGetShaderiv(vertex_shader, GL_COMPILE_STATUS):
        error_log = glGetShaderInfoLog(vertex_shader).decode()
        print(f"ERROR AL COMPILAR EL VERTEX SHADER ({os.path.basename(vertex_filepath)})\n{error_log}")
        glDeleteShader(vertex_shader)
        return 0

    # Compilar Fragment Shader
    fragment_shader = glCreateShader(GL_FRAGMENT_SHADER)
    glShaderSource(fragment_shader, fragment_src)
    glCompileShader(fragment_shader)
    if not glGetShaderiv(fragment_shader, GL_COMPILE_STATUS):
        error_log = glGetShaderInfoLog(fragment_shader).decode()
        print(f"ERROR AL COMPILAR EL FRAGMENT SHADER ({os.path.basename(fragment_filepath)})\n{error_log}")
        glDeleteShader(vertex_shader)
        glDeleteShader(fragment_shader)
        return 0

    # Crear y enlazar el programa del Shader
    shader_program = glCreateProgram()
    glAttachShader(shader_program, vertex_shader)
    glAttachShader(shader_program, fragment_shader)
    glLinkProgram(shader_program)

    if not glGetProgramiv(shader_program, GL_LINK_STATUS):
        error_log = glGetProgramInfoLog(shader_program).decode()
        print(f"ERROR AL ENLAZAR EL PROGRAMA DEL SHADER\n{error_log}")
        glDeleteProgram(shader_program)
        glDeleteShader(vertex_shader)
        glDeleteShader(fragment_shader)
        return 0

    # Los shaders ya no son necesarios una vez enlazados
    glDeleteShader(vertex_shader)
    glDeleteShader(fragment_shader)

    return shader_program