from OpenGL.GL import (
    glGenVertexArrays, glBindVertexArray, glGenBuffers, glBindBuffer, glBufferData,
    glEnableVertexAttribArray, glVertexAttribPointer, glDrawArrays, glUseProgram,
    GL_ARRAY_BUFFER, GL_STATIC_DRAW, GL_FLOAT, GL_FALSE, GL_LINES,
    glDrawElements, GL_ELEMENT_ARRAY_BUFFER, GL_UNSIGNED_INT
)
import numpy as np
import ctypes
import pyrr
from src.utils.Config import create_shader_program


class PivotGizmo:
    def __init__(self):
        program_folder = __file__.replace('src\\ui\\PivotGizmo.py', '')
        # Use a simple custom shader for the pivot gizmo so it doesn't rely on the voxel shader inputs
        self.program = create_shader_program(program_folder + "shaders/pivotGizmo.vert", program_folder + "shaders/pivotGizmo.frag")

        # Vertices for three axis lines (X, Y, Z). Each vertex: x, y, z, r, g, b
        # Lines are centered at the origin: each axis goes from -0.5 to +0.5 in its direction
        vertices = np.array([
            # X axis (red)
            -0.5, 0.0, 0.0,  1.0, 0.0, 0.0,
             0.5, 0.0, 0.0,  1.0, 0.0, 0.0,
            # Y axis (green)
            0.0, -0.5, 0.0,  0.0, 1.0, 0.0,
            0.0,  0.5, 0.0,  0.0, 1.0, 0.0,
            # Z axis (blue)
            0.0, 0.0, -0.5,  0.0, 0.0, 1.0,
            0.0, 0.0,  0.5,  0.0, 0.0, 1.0,
        ], dtype=np.float32)

        # Indices for drawing the three lines (pairs)
        indices = np.array([
            0, 1,  # X
            2, 3,  # Y
            4, 5   # Z
        ], dtype=np.uint32)

        self.vertex_count = len(indices)

        self.vao = glGenVertexArrays(1)
        glBindVertexArray(self.vao)

        self.vbo = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)

        # Create and fill element buffer (EBO)
        self.ebo = glGenBuffers(1)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.ebo)
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, indices.nbytes, indices, GL_STATIC_DRAW)

        # Position attribute
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 24, ctypes.c_void_p(0))
        # Color attribute
        glEnableVertexAttribArray(1)
        glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, 24, ctypes.c_void_p(12))

        glBindVertexArray(0)

    def render(self, projection, view, pivot_voxel):
        if not self.program:
            return
        glUseProgram(self.program)
        px, py, pz = pivot_voxel
        translation = pyrr.matrix44.create_from_translation(np.array([px + 0.5, py + 0.5, pz + 0.5], dtype=np.float32))
        scale = pyrr.matrix44.create_from_scale(np.array([0.5, 0.5, 0.5], dtype=np.float32))
        model = pyrr.matrix44.multiply(scale, translation)
        try:
            from OpenGL.GL import glUniformMatrix4fv, glGetUniformLocation
            glUniformMatrix4fv(glGetUniformLocation(self.program, "projection"), 1, GL_FALSE, projection)
            glUniformMatrix4fv(glGetUniformLocation(self.program, "view"), 1, GL_FALSE, view)
            glUniformMatrix4fv(glGetUniformLocation(self.program, "model"), 1, GL_FALSE, model)
        except Exception:
            pass
        glBindVertexArray(self.vao)
        glDrawElements(GL_LINES, self.vertex_count, GL_UNSIGNED_INT, ctypes.c_void_p(0))
