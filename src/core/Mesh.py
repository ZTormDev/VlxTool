# Mesh.py
from src.utils.Config import data_type_vertex
import numpy as np
from OpenGL.GL import (
    glGenVertexArrays, glBindVertexArray, glGenBuffers, glBindBuffer, glBufferData,
    glEnableVertexAttribArray, glVertexAttribPointer, glVertexAttribIPointer, glDeleteVertexArrays,
    GL_ARRAY_BUFFER, GL_STATIC_DRAW, GL_FLOAT, GL_UNSIGNED_INT
)
from OpenGL.GL import GL_ELEMENT_ARRAY_BUFFER, GL_FALSE
import ctypes

class Mesh:
    def __init__(self, vertices, indices):
        self.vertex_count = len(vertices)
        self.index_count = len(indices)

        self.vao = glGenVertexArrays(1)
        glBindVertexArray(self.vao)

        self.vbo = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)
        
        self.ebo = glGenBuffers(1)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.ebo)
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, indices.nbytes, indices, GL_STATIC_DRAW)

        # Atributo 0: Posición (offset 0)
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, data_type_vertex.itemsize, ctypes.c_void_p(0))

        # Atributo 1: Normal (offset 12)
        glEnableVertexAttribArray(1)
        glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, data_type_vertex.itemsize, ctypes.c_void_p(12))

        # Atributo 2: Índice de color (offset 24)
        glEnableVertexAttribArray(2)
        glVertexAttribIPointer(2, 1, GL_UNSIGNED_INT, data_type_vertex.itemsize, ctypes.c_void_p(24))
        
        # --- NUEVO ATRIBUTO PARA AO ---
        # Atributo 3: Oclusión Ambiental (offset 28)
        glEnableVertexAttribArray(3)
        glVertexAttribPointer(3, 1, GL_FLOAT, GL_FALSE, data_type_vertex.itemsize, ctypes.c_void_p(28))

        glBindVertexArray(0)

    def destroy(self):
        glDeleteVertexArrays(1, (self.vao,))