# Highlight.py
import os
from OpenGL.GL import (
    glGenVertexArrays, glBindVertexArray, glGenBuffers, glBindBuffer, glBufferData,
    glEnableVertexAttribArray, glVertexAttribPointer, glBindVertexArray, glUseProgram,
    glDisable, glEnable, glBlendFunc, glDrawElements, GL_ARRAY_BUFFER, GL_STATIC_DRAW,
    GL_FLOAT, GL_FALSE, GL_CULL_FACE, GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA, GL_TRIANGLES,
    GL_UNSIGNED_INT
)
from OpenGL.GL import (
    glUniformMatrix4fv, glGetUniformLocation, GL_ELEMENT_ARRAY_BUFFER, GL_BLEND
)
import numpy as np
import ctypes
import pyrr
from src.utils.Config import create_shader_program

class Highlight:
    def __init__(self):
        program_folder = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) + "/"
        self.program = create_shader_program(program_folder + "shaders/highlight.vert", program_folder + "shaders/highlight.frag")
        
        vertices = np.array([-0.501, 0.501, 0.0, -0.501, -0.501, 0.0, 0.501, -0.501, 0.0, 0.501, 0.501, 0.0], dtype=np.float32)
        indices = np.array([0, 1, 2, 0, 2, 3], dtype=np.uint32)

        self.vao = glGenVertexArrays(1)
        glBindVertexArray(self.vao)
        vbo = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, vbo)
        glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)
        ebo = glGenBuffers(1)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, ebo)
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, indices.nbytes, indices, GL_STATIC_DRAW)
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 0, ctypes.c_void_p(0))
        glBindVertexArray(0)

    def render(self, projection, view, chunk_model, hit_pos, hit_normal):
        if self.program == 0:
            return

        # --- CORRECCIONES AQUÍ ---
        # 1. Desactivamos el culling de caras para el resaltado
        glDisable(GL_CULL_FACE)
        
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glUseProgram(self.program)
        
        rotation_matrix = pyrr.matrix44.create_identity(dtype=np.float32)
        if hit_normal[1] > 0.9: # Top (+Y)
            rotation_matrix = pyrr.matrix44.create_from_x_rotation(-np.pi / 2)
        elif hit_normal[1] < -0.9: # Bottom (-Y)
            rotation_matrix = pyrr.matrix44.create_from_x_rotation(np.pi / 2)
        elif hit_normal[0] > 0.9: # Right (+X)
            rotation_matrix = pyrr.matrix44.create_from_y_rotation(np.pi / 2)
        elif hit_normal[0] < -0.9: # Left (-X)
            rotation_matrix = pyrr.matrix44.create_from_y_rotation(-np.pi / 2)
        elif hit_normal[2] < -0.9: # Back (-Z)
            rotation_matrix = pyrr.matrix44.create_from_y_rotation(np.pi)

        voxel_center = np.array(hit_pos, dtype=np.float32) + 0.5
        face_offset = np.array(hit_normal, dtype=np.float32) * 0.502
        final_position = voxel_center + face_offset
        translation_matrix = pyrr.matrix44.create_from_translation(final_position)
        
        model_matrix = pyrr.matrix44.multiply(rotation_matrix, translation_matrix)

        glUniformMatrix4fv(glGetUniformLocation(self.program, "projection"), 1, GL_FALSE, projection)
        glUniformMatrix4fv(glGetUniformLocation(self.program, "view"), 1, GL_FALSE, view)
        glUniformMatrix4fv(glGetUniformLocation(self.program, "model"), 1, GL_FALSE, model_matrix)
        
        glBindVertexArray(self.vao)
        glDrawElements(GL_TRIANGLES, 6, GL_UNSIGNED_INT, None)
        
        glDisable(GL_BLEND)
        
        # 2. Reactivamos el culling de caras para el resto de la escena
        glEnable(GL_CULL_FACE)