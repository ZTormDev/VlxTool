# src/Grid.py
import os
import numpy as np
from OpenGL.GL import *
import ctypes
import pyrr
from src.Config import create_shader_program

class Grid:
    def __init__(self, width, depth, height):
        program_folder = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/"
        self.program = create_shader_program(program_folder + "shaders/grid.vert", program_folder + "shaders/grid.frag")

        vertices = []
        
        # --- LÓGICA DE VÉRTICES CORREGIDA Y SIMPLIFICADA ---

        # Dibuja una cuadrícula completa para cada una de las 6 caras del cubo.
        
        # Cara Inferior y Superior (Y = 0, Y = height)
        for y_level in [0, height]:
            for i in range(width + 1):
                vertices.extend([i, y_level, 0,   i, y_level, depth]) # Líneas en dirección Z
            for i in range(depth + 1):
                vertices.extend([0, y_level, i,   width, y_level, i]) # Líneas en dirección X

        # Cara Izquierda y Derecha (X = 0, X = width)
        for x_level in [0, width]:
            for i in range(height + 1):
                vertices.extend([x_level, i, 0,   x_level, i, depth]) # Líneas en dirección Z
            for i in range(depth + 1):
                vertices.extend([x_level, 0, i,   x_level, height, i]) # Líneas en dirección Y

        # Cara Trasera y Frontal (Z = 0, Z = depth)
        for z_level in [0, depth]:
            for i in range(height + 1):
                vertices.extend([0, i, z_level,   width, i, z_level]) # Líneas en dirección X
            for i in range(width + 1):
                vertices.extend([i, 0, z_level,   i, height, z_level]) # Líneas en dirección Y

        vertices = np.array(vertices, dtype=np.float32)
        self.vertex_count = len(vertices) // 3

        self.vao = glGenVertexArrays(1)
        glBindVertexArray(self.vao)
        
        self.vbo = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)
        
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 0, ctypes.c_void_p(0))
        
        glBindVertexArray(0)

        self.model_matrix = pyrr.matrix44.create_identity(dtype=np.float32)

    def render(self, projection_matrix, view_matrix):
        if self.program == 0:
            return

        glUseProgram(self.program)
        glDisable(GL_CULL_FACE) # <-- Desactivas el culling para que se vean todas las líneas
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        
        glUniformMatrix4fv(glGetUniformLocation(self.program, "projection"), 1, GL_FALSE, projection_matrix)
        glUniformMatrix4fv(glGetUniformLocation(self.program, "view"), 1, GL_FALSE, view_matrix)
        glUniformMatrix4fv(glGetUniformLocation(self.program, "model"), 1, GL_FALSE, self.model_matrix)
        
        glBindVertexArray(self.vao)
        glDrawArrays(GL_LINES, 0, self.vertex_count)
        
        glDisable(GL_BLEND)
        glEnable(GL_CULL_FACE) # <-- AÑADE ESTA LÍNEA para restaurar el estado

    def destroy(self):
        glDeleteVertexArrays(1, (self.vao,))
        glDeleteBuffers(1, (self.vbo,))
        if self.program:
            glDeleteProgram(self.program)