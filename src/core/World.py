# World.py
import numpy as np
from src.core.Chunk import Chunk

class World:
    def __init__(self, chunk_size=32, world_size_in_chunks=1):
        self.chunk_size = chunk_size
        self.world_size_in_chunks = world_size_in_chunks
        
        self.chunks = {}
        self.dirty_chunks = set()

        self.create_test_world()

    def create_test_world(self):
        for cx in range(self.world_size_in_chunks):
            for cz in range(self.world_size_in_chunks):
                chunk_pos = (cx, cz)
                chunk = Chunk(self, chunk_pos, self.chunk_size)
                self.chunks[chunk_pos] = chunk
                self.dirty_chunks.add(chunk)

    def get_local_pos(self, x, y, z):
        """ Convierte coordenadas globales a (chunk_pos, local_pos). """
        chunk_x, local_x = divmod(x, self.chunk_size)
        chunk_z, local_z = divmod(z, self.chunk_size)
        return ((chunk_x, chunk_z), (local_x, y, local_z))

    def is_solid(self, x, y, z):
        """ Comprueba si un bloque es sólido en coordenadas globales. """
        if not (0 <= x < self.chunk_size * self.world_size_in_chunks and \
                0 <= y < self.chunk_size and \
                0 <= z < self.chunk_size * self.world_size_in_chunks):
            return False

        chunk_pos, local_pos = self.get_local_pos(x, y, z)
        if chunk_pos not in self.chunks:
            return False
        return self.chunks[chunk_pos].is_solid(local_pos[0], local_pos[1], local_pos[2])

    def set_voxel(self, x, y, z, block_type):
        """ Coloca un bloque y marca los chunks afectados como 'sucios'. """
        # Accept either an Enum-like block_type with a `.value` attribute or a plain int
        try:
            block_id = block_type.value if hasattr(block_type, 'value') else int(block_type)
        except Exception:
            # Fallback: try to coerce to int, else default to 0 (Air)
            try:
                block_id = int(block_type)
            except Exception:
                block_id = 0

        chunk_pos, local_pos = self.get_local_pos(x, y, z)
        
        if chunk_pos not in self.chunks:
            return

        chunk = self.chunks[chunk_pos]

        # Ensure we pass a numeric block id into the chunk (uint array)
        chunk.set_voxel(local_pos[0], local_pos[1], local_pos[2], block_id)

        self.dirty_chunks.add(chunk)

        # Si el bloque está en un borde, marcamos también el chunk vecino
        lx, ly, lz = local_pos
        if lx == 0:
            neighbor_chunk_pos = (chunk_pos[0] - 1, chunk_pos[1])
            if neighbor_chunk_pos in self.chunks: self.dirty_chunks.add(self.chunks[neighbor_chunk_pos])
        elif lx == self.chunk_size - 1:
            neighbor_chunk_pos = (chunk_pos[0] + 1, chunk_pos[1])
            if neighbor_chunk_pos in self.chunks: self.dirty_chunks.add(self.chunks[neighbor_chunk_pos])
        
        if lz == 0:
            neighbor_chunk_pos = (chunk_pos[0], chunk_pos[1] - 1)
            if neighbor_chunk_pos in self.chunks: self.dirty_chunks.add(self.chunks[neighbor_chunk_pos])
        elif lz == self.chunk_size - 1:
            neighbor_chunk_pos = (chunk_pos[0], chunk_pos[1] + 1)
            if neighbor_chunk_pos in self.chunks: self.dirty_chunks.add(self.chunks[neighbor_chunk_pos])
        
    def update_dirty_chunks(self):
        """ Reconstruye la malla de todos los chunks marcados como 'sucios'. """
        # Convertimos a lista para evitar problemas si el set se modifica durante la iteración
        for chunk in list(self.dirty_chunks):
            chunk.build_mesh()
        self.dirty_chunks.clear()