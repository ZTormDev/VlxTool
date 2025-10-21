# Skybox.py
import os
from OpenGL.GL import *
import numpy as np
import ctypes
from src.Config import create_shader_program

class Skybox:
    def __init__(self):
        program_folder = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/"
        self.program = create_shader_program(program_folder + "shaders/skybox.vert", program_folder + "shaders/skybox.frag")
        self.vao, self.vbo = self.get_vao()

    def get_vao(self):
        # --- VÉRTICES CORREGIDOS PARA UN CUBO DE SKYBOX ---
        # 36 vértices (12 triángulos x 3 vértices)
        vertices = np.array([
            -1.0,  1.0, -1.0, -1.0, -1.0, -1.0,  1.0, -1.0, -1.0,
             1.0, -1.0, -1.0,  1.0,  1.0, -1.0, -1.0,  1.0, -1.0,
            -1.0, -1.0,  1.0, -1.0, -1.0, -1.0, -1.0,  1.0, -1.0,
            -1.0,  1.0, -1.0, -1.0,  1.0,  1.0, -1.0, -1.0,  1.0,
             1.0, -1.0, -1.0,  1.0, -1.0,  1.0,  1.0,  1.0,  1.0,
             1.0,  1.0,  1.0,  1.0,  1.0, -1.0,  1.0, -1.0, -1.0,
            -1.0, -1.0,  1.0, -1.0,  1.0,  1.0,  1.0,  1.0,  1.0,
             1.0,  1.0,  1.0,  1.0, -1.0,  1.0, -1.0, -1.0,  1.0,
            -1.0,  1.0, -1.0,  1.0,  1.0, -1.0,  1.0,  1.0,  1.0,
             1.0,  1.0,  1.0, -1.0,  1.0,  1.0, -1.0,  1.0, -1.0,
            -1.0, -1.0, -1.0, -1.0, -1.0,  1.0,  1.0, -1.0, -1.0,
             1.0, -1.0, -1.0, -1.0, -1.0,  1.0,  1.0, -1.0,  1.0
        ], dtype=np.float32)

        vao = glGenVertexArrays(1)
        glBindVertexArray(vao)
        vbo = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, vbo)
        glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 0, ctypes.c_void_p(0))
        glBindVertexArray(0)
        return vao, vbo

    def render(self, projection_matrix, view_matrix):
        view_matrix_skybox = np.copy(view_matrix)
        view_matrix_skybox[3, :3] = 0
        
        glDepthFunc(GL_LEQUAL)
        
        glUseProgram(self.program)
        glUniformMatrix4fv(glGetUniformLocation(self.program, "projection"), 1, GL_FALSE, projection_matrix)
        glUniformMatrix4fv(glGetUniformLocation(self.program, "view"), 1, GL_FALSE, view_matrix_skybox)

        glBindVertexArray(self.vao)
        # Ya no se bindea ninguna textura
        glDrawArrays(GL_TRIANGLES, 0, 36)

        glDepthFunc(GL_LESS)
        glBindVertexArray(0)