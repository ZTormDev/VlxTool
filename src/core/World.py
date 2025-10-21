# World.py
import numpy as np

class World:
    def __init__(self, chunk_size=32, world_size_in_chunks=2):
        self.base_chunk_size = chunk_size
        self.world_size_in_chunks = world_size_in_chunks

        # Total world size in voxels per axis
        self.total_size = self.base_chunk_size * self.world_size_in_chunks

        self.chunks = {}
        self.dirty_chunks = set()

        # Lazy import to avoid circulars at module import time
        from src.core.Chunk import Chunk
        full_chunk = Chunk(self, (0, 0), self.total_size)
        self.chunks[(0, 0)] = full_chunk
        self.dirty_chunks.add(full_chunk)

        # Default pivot: bottom-center of the world in voxel coordinates
        world_coord_size = self.total_size
        self.pivot = (world_coord_size // 2, 0, world_coord_size // 2)
        
    def get_local_pos(self, x, y, z):
        """Convierte coordenadas globales a (chunk_pos, local_pos).

        Since the world is now represented as a single large chunk located at
        (0,0) with size == total_size, we return chunk_pos (0,0) and local_pos
        equal to the global coordinates (assuming they are in-bounds).
        """
        # Clamp/normalize to integers
        lx, ly, lz = int(x), int(y), int(z)
        return ((0, 0), (lx, ly, lz))

    def is_solid(self, x, y, z):
        """ Comprueba si un bloque es sólido en coordenadas globales. """
        # Check bounds against total world size
        if not (0 <= x < self.total_size and \
                0 <= y < self.total_size and \
                0 <= z < self.total_size):
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

        # Mark the full chunk dirty (we only have one)
        self.dirty_chunks.add(chunk)
        
    def update_dirty_chunks(self):
        """ Reconstruye la malla de todos los chunks marcados como 'sucios'. """
        # Convertimos a lista para evitar problemas si el set se modifica durante la iteración
        for chunk in list(self.dirty_chunks):
            chunk.build_mesh()
        self.dirty_chunks.clear()

    def get_voxel(self, x, y, z):
        """Return voxel id at global coordinates (x,y,z). Returns 0 for out-of-bounds or air."""
        try:
            if not (0 <= x < self.total_size and 0 <= y < self.total_size and 0 <= z < self.total_size):
                return 0
            chunk_pos, local_pos = self.get_local_pos(x, y, z)
            chunk = self.chunks.get(chunk_pos)
            if not chunk:
                return 0
            lx, ly, lz = local_pos
            return int(chunk.voxels[lx, ly, lz])
        except Exception:
            return 0