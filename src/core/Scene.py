# src/Scene.py
import numpy as np
import pyrr
from OpenGL.GL import (
    glUseProgram, glUniform3fv, glGetUniformLocation, glUniformMatrix4fv, glEnable, glDrawElements,
    GL_FALSE, GL_TRIANGLES, GL_UNSIGNED_INT, GL_CULL_FACE
)
from OpenGL.GL import glBindVertexArray

from src.core.World import World
from src.ui.Grid import Grid
from src.core.Sun import Sun
from src.ui.Highlight import Highlight
from src.ui.PivotGizmo import PivotGizmo

class Scene:
    def __init__(self, block_type_enum, block_colors_dict):
        self.world_size = 3
        chunk_dimension = 32
        world_coord_size = chunk_dimension * self.world_size

        self.world = World(chunk_size=chunk_dimension, world_size_in_chunks=self.world_size)
        self.grid = Grid(width=world_coord_size, depth=world_coord_size, height=world_coord_size)
        self.sun = Sun()
        self.highlighter = Highlight()
        self.pivot_gizmo = PivotGizmo()
        
        self.max_block_types = 16
        self.block_palette_array = np.zeros((self.max_block_types, 3), dtype=np.float32)
        for block_type, color in block_colors_dict.items():
            if int(block_type) < self.max_block_types:
                self.block_palette_array[int(block_type)] = color

    def render(self, projection_matrix, view_matrix, voxel_shader, hit_voxel_pos, hit_voxel_normal):
        self.grid.render(projection_matrix, view_matrix)
        
        # Render Voxel World
        glUseProgram(voxel_shader)
        
        # Uniforms
        glUniform3fv(glGetUniformLocation(voxel_shader, "u_block_palette"), self.max_block_types, self.block_palette_array)
        glUniform3fv(glGetUniformLocation(voxel_shader, "u_sun_direction"), 1, self.sun.direction)
        glUniform3fv(glGetUniformLocation(voxel_shader, "u_sun_color"), 1, self.sun.color)
        glUniformMatrix4fv(glGetUniformLocation(voxel_shader, "view"), 1, GL_FALSE, view_matrix)
        glUniformMatrix4fv(glGetUniformLocation(voxel_shader, "projection"), 1, GL_FALSE, projection_matrix)
        
        glEnable(GL_CULL_FACE)
        for chunk in self.world.chunks.values():
            if chunk.mesh:
                glUniformMatrix4fv(glGetUniformLocation(voxel_shader, "model"), 1, GL_FALSE, chunk.model_matrix)
                glBindVertexArray(chunk.mesh.vao)
                glDrawElements(GL_TRIANGLES, chunk.mesh.index_count, GL_UNSIGNED_INT, None)

        # Render Highlighter
        if hit_voxel_pos and hit_voxel_normal:
            identity_matrix = pyrr.matrix44.create_identity(dtype=np.float32)
            self.highlighter.render(projection_matrix, view_matrix, identity_matrix, hit_voxel_pos, hit_voxel_normal)

        # Render pivot gizmo using the world's pivot
        try:
            pivot = self.world.pivot
            if pivot is not None:
                self.pivot_gizmo.render(projection_matrix, view_matrix, pivot)
        except Exception:
            pass

    def destroy(self):
        self.grid.destroy()
        for chunk in self.world.chunks.values():
            if chunk.mesh:
                chunk.mesh.destroy()