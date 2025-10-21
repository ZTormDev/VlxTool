# src/Chunk.py
import numpy as np
from src.utils.Config import data_type_vertex
from src.core.Mesh import Mesh
import pyrr

class Chunk:
    def __init__(self, world, position, size):
        self.world = world
        self.position = position # (cx, cz)
        self.size = size
        
        self.voxels = np.zeros((size, size, size), dtype=np.uint32)
        self.mesh = None
        
        self.model_matrix = pyrr.matrix44.create_from_translation(
            [position[0] * size, 0, position[1] * size], dtype=np.float32)

    def set_voxel(self, x, y, z, block_type):
        if 0 <= x < self.size and 0 <= y < self.size and 0 <= z < self.size:
            self.voxels[x, y, z] = block_type
    
    def is_solid(self, x, y, z):
        # Aquí se esperan coordenadas LOCALES (relativas al chunk).
        # Comprobamos que estén dentro del rango del chunk antes de acceder al array.
        if not (0 <= x < self.size and 0 <= y < self.size and 0 <= z < self.size):
            return False
        # El bloque 0 (Air) no es sólido.
        return self.voxels[x, y, z] > 0

    def get_global_pos(self, x, y, z):
        return (self.position[0] * self.size + x, y, self.position[1] * self.size + z)

    def calculate_ao(self, side1, side2, corner):
        """
        Minecraft-style Ambient Occlusion.

        The standard approach counts occluding neighbors around a vertex:
        - side1 and side2 are the two edge-adjacent blocks (0 or 1)
        - corner is the diagonal block at the vertex (0 or 1)

        The corner only contributes when both adjacent sides are present.
        We map the resulting occlusion_count (0..3) to a discrete AO factor
        commonly used in voxel engines (approximate Minecraft):
            occlusion_count  AO factor
                    0            1.00 (fully lit)
                    1            0.80
                    2            0.60
                    3            0.40 (most occluded)

        Returns a float in [0.4, 1.0]. This is faster and yields the
        familiar crisp corners seen in Minecraft-like rendering.
        """
        s = 1 if side1 else 0
        t = 1 if side2 else 0
        c = 1 if corner else 0

        corner_contrib = c if (s and t) else 0
        occlusion_count = s + t + corner_contrib  # 0..3

        # Map occlusion count to a discrete factor
        ao_lookup = (1.0, 0.8, 0.6, 0.4)
        return float(ao_lookup[occlusion_count])

    def calculate_ao_enhanced(self, vx, vy, vz):
        """
        Enhanced AO: sample the 8 voxels that touch the given vertex
        located at integer coordinates (vx, vy, vz). The 8 voxels have
        coordinates (vx-1 or vx, vy-1 or vy, vz-1 or vz).

        We count occupied voxels among those 8 and map the fraction to a
        factor in [0.4, 1.0] (1.0 = fully lit, 0.4 = most occluded).
        """
        count = 0
        for dx in (-1, 0):
            for dy in (-1, 0):
                for dz in (-1, 0):
                    if self.world.is_solid(vx + dx, vy + dy, vz + dz):
                        count += 1
        # normalize 0..8 -> 0..1
        frac = count / 8.0
        # map to AO factor: 1.0 -> 0.4 linearly (preserve familiar range)
        ao = 1.0 - 0.6 * frac
        if ao < 0.4: ao = 0.4
        if ao > 1.0: ao = 1.0
        return float(ao)

    def build_mesh(self):
        vertex_list, index_list = [], []
        vertex_index_counter = 0

        for x in range(self.size):
            for y in range(self.size):
                for z in range(self.size):
                    block_type = self.voxels[x, y, z]
                    if block_type == 0: # 0 es Aire
                        continue
                    
                    gx, gy, gz = self.get_global_pos(x, y, z)

                    # --- ✨ INICIO DE LA CORRECCIÓN ✨ ---
                    # Se ha modificado la creación de vértices en las 6 caras
                    # para que coincida con la estructura de data_type_vertex.

                    # Cara +X (Derecha)
                    if not self.world.is_solid(gx + 1, gy, gz):
                        n = {
                            'b': self.world.is_solid(gx+1, gy-1, gz),
                            't': self.world.is_solid(gx+1, gy+1, gz),
                            'l': self.world.is_solid(gx+1, gy, gz-1),
                            'r': self.world.is_solid(gx+1, gy, gz+1),
                            'bl': self.world.is_solid(gx+1, gy-1, gz-1),
                            'br': self.world.is_solid(gx+1, gy-1, gz+1),
                            'tl': self.world.is_solid(gx+1, gy+1, gz-1),
                            'tr': self.world.is_solid(gx+1, gy+1, gz+1)
                        }
                        ao = [
                            self.calculate_ao(n['t'], n['l'], n['tl']),
                            self.calculate_ao(n['b'], n['l'], n['bl']),
                            self.calculate_ao(n['b'], n['r'], n['br']),
                            self.calculate_ao(n['t'], n['r'], n['tr'])
                        ]
                        e0 = self.calculate_ao_enhanced(gx + 1, gy + 1, gz + 0)
                        e1 = self.calculate_ao_enhanced(gx + 1, gy + 0, gz + 0)
                        e2 = self.calculate_ao_enhanced(gx + 1, gy + 0, gz + 1)
                        e3 = self.calculate_ao_enhanced(gx + 1, gy + 1, gz + 1)
                        fa0 = min(ao[0], e0)
                        fa1 = min(ao[1], e1)
                        fa2 = min(ao[2], e2)
                        fa3 = min(ao[3], e3)
                        v = [
                            ((x+1, y+1, z),   (1,0,0), block_type, fa0),
                            ((x+1, y, z),     (1,0,0), block_type, fa1),
                            ((x+1, y, z+1),   (1,0,0), block_type, fa2),
                            ((x+1, y+1, z+1), (1,0,0), block_type, fa3)
                        ]
                        vertex_list.extend(v)
                        i = vertex_index_counter
                        s1 = fa0 + fa2
                        s2 = fa1 + fa3
                        if s1 > s2:
                            index_list.extend([i, i+1, i+2, i, i+2, i+3])
                        elif s1 < s2:
                            index_list.extend([i, i+1, i+3, i+3, i+1, i+2])
                        else:
                            if ((gx + gy + gz) & 1):
                                index_list.extend([i, i+1, i+2, i, i+2, i+3])
                            else:
                                index_list.extend([i, i+1, i+3, i+3, i+1, i+2])
                        vertex_index_counter += 4

                    # Cara -X (Izquierda)
                    if not self.world.is_solid(gx - 1, gy, gz):
                        n = {
                            'b': self.world.is_solid(gx-1, gy-1, gz),
                            't': self.world.is_solid(gx-1, gy+1, gz),
                            'l': self.world.is_solid(gx-1, gy, gz+1),
                            'r': self.world.is_solid(gx-1, gy, gz-1),
                            'bl': self.world.is_solid(gx-1, gy-1, gz+1),
                            'br': self.world.is_solid(gx-1, gy-1, gz-1),
                            'tl': self.world.is_solid(gx-1, gy+1, gz+1),
                            'tr': self.world.is_solid(gx-1, gy+1, gz-1)
                        }
                        ao = [
                            self.calculate_ao(n['t'], n['l'], n['tl']),
                            self.calculate_ao(n['b'], n['l'], n['bl']),
                            self.calculate_ao(n['b'], n['r'], n['br']),
                            self.calculate_ao(n['t'], n['r'], n['tr'])
                        ]
                        e0 = self.calculate_ao_enhanced(gx + 0, gy + 1, gz + 1)
                        e1 = self.calculate_ao_enhanced(gx + 0, gy + 0, gz + 1)
                        e2 = self.calculate_ao_enhanced(gx + 0, gy + 0, gz + 0)
                        e3 = self.calculate_ao_enhanced(gx + 0, gy + 1, gz + 0)
                        fa0 = min(ao[0], e0)
                        fa1 = min(ao[1], e1)
                        fa2 = min(ao[2], e2)
                        fa3 = min(ao[3], e3)
                        v = [
                            ((x, y+1, z+1), (-1,0,0), block_type, fa0),
                            ((x, y, z+1),   (-1,0,0), block_type, fa1),
                            ((x, y, z),     (-1,0,0), block_type, fa2),
                            ((x, y+1, z),   (-1,0,0), block_type, fa3)
                        ]
                        vertex_list.extend(v)
                        i = vertex_index_counter
                        s1 = fa0 + fa2
                        s2 = fa1 + fa3
                        if s1 > s2:
                            index_list.extend([i, i+1, i+2, i, i+2, i+3])
                        elif s1 < s2:
                            index_list.extend([i, i+1, i+3, i+3, i+1, i+2])
                        else:
                            if ((gx + gy + gz) & 1):
                                index_list.extend([i, i+1, i+2, i, i+2, i+3])
                            else:
                                index_list.extend([i, i+1, i+3, i+3, i+1, i+2])
                        vertex_index_counter += 4

                    # Cara +Y (Arriba)
                    if not self.world.is_solid(gx, gy + 1, gz):
                        n = {
                            'b': self.world.is_solid(gx, gy+1, gz-1),
                            't': self.world.is_solid(gx, gy+1, gz+1),
                            'l': self.world.is_solid(gx-1, gy+1, gz),
                            'r': self.world.is_solid(gx+1, gy+1, gz),
                            'bl': self.world.is_solid(gx-1, gy+1, gz-1),
                            'br': self.world.is_solid(gx+1, gy+1, gz-1),
                            'tl': self.world.is_solid(gx-1, gy+1, gz+1),
                            'tr': self.world.is_solid(gx+1, gy+1, gz+1)
                        }
                        ao = [
                            self.calculate_ao(n['t'], n['l'], n['tl']),
                            self.calculate_ao(n['b'], n['l'], n['bl']),
                            self.calculate_ao(n['b'], n['r'], n['br']),
                            self.calculate_ao(n['t'], n['r'], n['tr'])
                        ]
                        e0 = self.calculate_ao_enhanced(gx + 0, gy + 1, gz + 1)
                        e1 = self.calculate_ao_enhanced(gx + 0, gy + 1, gz + 0)
                        e2 = self.calculate_ao_enhanced(gx + 1, gy + 1, gz + 0)
                        e3 = self.calculate_ao_enhanced(gx + 1, gy + 1, gz + 1)
                        fa0 = min(ao[0], e0)
                        fa1 = min(ao[1], e1)
                        fa2 = min(ao[2], e2)
                        fa3 = min(ao[3], e3)
                        v = [
                            ((x, y+1, z+1),   (0,1,0), block_type, fa0),
                            ((x, y+1, z),     (0,1,0), block_type, fa1),
                            ((x+1, y+1, z),   (0,1,0), block_type, fa2),
                            ((x+1, y+1, z+1), (0,1,0), block_type, fa3)
                        ]
                        vertex_list.extend(v)
                        i = vertex_index_counter
                        s1 = fa0 + fa2
                        s2 = fa1 + fa3
                        if s1 > s2:
                            index_list.extend([i, i+1, i+2, i, i+2, i+3])
                        elif s1 < s2:
                            index_list.extend([i, i+1, i+3, i+3, i+1, i+2])
                        else:
                            if ((gx + gy + gz) & 1):
                                index_list.extend([i, i+1, i+2, i, i+2, i+3])
                            else:
                                index_list.extend([i, i+1, i+3, i+3, i+1, i+2])
                        vertex_index_counter += 4

                    # Cara -Y (Abajo)
                    if not self.world.is_solid(gx, gy - 1, gz):
                        n = {
                            'b': self.world.is_solid(gx, gy-1, gz-1),
                            't': self.world.is_solid(gx, gy-1, gz+1),
                            'l': self.world.is_solid(gx-1, gy-1, gz),
                            'r': self.world.is_solid(gx+1, gy-1, gz),
                            'bl': self.world.is_solid(gx-1, gy-1, gz-1),
                            'br': self.world.is_solid(gx+1, gy-1, gz-1),
                            'tl': self.world.is_solid(gx-1, gy-1, gz+1),
                            'tr': self.world.is_solid(gx+1, gy-1, gz+1)
                        }
                        ao = [
                            self.calculate_ao(n['t'], n['r'], n['tr']),
                            self.calculate_ao(n['b'], n['r'], n['br']),
                            self.calculate_ao(n['b'], n['l'], n['bl']),
                            self.calculate_ao(n['t'], n['l'], n['tl'])
                        ]
                        e0 = self.calculate_ao_enhanced(gx + 1, gy + 0, gz + 1)
                        e1 = self.calculate_ao_enhanced(gx + 1, gy + 0, gz + 0)
                        e2 = self.calculate_ao_enhanced(gx + 0, gy + 0, gz + 0)
                        e3 = self.calculate_ao_enhanced(gx + 0, gy + 0, gz + 1)
                        fa0 = min(ao[0], e0)
                        fa1 = min(ao[1], e1)
                        fa2 = min(ao[2], e2)
                        fa3 = min(ao[3], e3)
                        v = [
                            ((x+1, y, z+1), (0,-1,0), block_type, fa0),
                            ((x+1, y, z),   (0,-1,0), block_type, fa1),
                            ((x, y, z),     (0,-1,0), block_type, fa2),
                            ((x, y, z+1),   (0,-1,0), block_type, fa3)
                        ]
                        vertex_list.extend(v)
                        i = vertex_index_counter
                        s1 = fa0 + fa2
                        s2 = fa1 + fa3
                        if s1 > s2:
                            index_list.extend([i, i+1, i+2, i, i+2, i+3])
                        elif s1 < s2:
                            index_list.extend([i, i+1, i+3, i+3, i+1, i+2])
                        else:
                            if ((gx + gy + gz) & 1):
                                index_list.extend([i, i+1, i+2, i, i+2, i+3])
                            else:
                                index_list.extend([i, i+1, i+3, i+3, i+1, i+2])
                        vertex_index_counter += 4

                    # Cara +Z (Frente)
                    if not self.world.is_solid(gx, gy, gz + 1):
                        n = {
                            'b': self.world.is_solid(gx, gy-1, gz+1),
                            't': self.world.is_solid(gx, gy+1, gz+1),
                            'l': self.world.is_solid(gx-1, gy, gz+1),
                            'r': self.world.is_solid(gx+1, gy, gz+1),
                            'bl': self.world.is_solid(gx-1, gy-1, gz+1),
                            'br': self.world.is_solid(gx+1, gy-1, gz+1),
                            'tl': self.world.is_solid(gx-1, gy+1, gz+1),
                            'tr': self.world.is_solid(gx+1, gy+1, gz+1)
                        }
                        ao = [
                            self.calculate_ao(n['t'], n['r'], n['tr']),
                            self.calculate_ao(n['b'], n['r'], n['br']),
                            self.calculate_ao(n['b'], n['l'], n['bl']),
                            self.calculate_ao(n['t'], n['l'], n['tl'])
                        ]
                        e0 = self.calculate_ao_enhanced(gx + 1, gy + 1, gz + 1)
                        e1 = self.calculate_ao_enhanced(gx + 1, gy + 0, gz + 1)
                        e2 = self.calculate_ao_enhanced(gx + 0, gy + 0, gz + 1)
                        e3 = self.calculate_ao_enhanced(gx + 0, gy + 1, gz + 1)
                        fa0 = min(ao[0], e0)
                        fa1 = min(ao[1], e1)
                        fa2 = min(ao[2], e2)
                        fa3 = min(ao[3], e3)
                        v = [
                            ((x+1, y+1, z+1), (0,0,1), block_type, fa0),
                            ((x+1, y, z+1),   (0,0,1), block_type, fa1),
                            ((x, y, z+1),     (0,0,1), block_type, fa2),
                            ((x, y+1, z+1),   (0,0,1), block_type, fa3)
                        ]
                        vertex_list.extend(v)
                        i = vertex_index_counter
                        s1 = fa0 + fa2
                        s2 = fa1 + fa3
                        if s1 > s2:
                            index_list.extend([i, i+1, i+2, i, i+2, i+3])
                        elif s1 < s2:
                            index_list.extend([i, i+1, i+3, i+3, i+1, i+2])
                        else:
                            if ((gx + gy + gz) & 1):
                                index_list.extend([i, i+1, i+2, i, i+2, i+3])
                            else:
                                index_list.extend([i, i+1, i+3, i+3, i+1, i+2])
                        vertex_index_counter += 4

                    # Cara -Z (Atrás)
                    if not self.world.is_solid(gx, gy, gz - 1):
                        n = {
                            'b': self.world.is_solid(gx, gy-1, gz-1),
                            't': self.world.is_solid(gx, gy+1, gz-1),
                            'l': self.world.is_solid(gx+1, gy, gz-1),
                            'r': self.world.is_solid(gx-1, gy, gz-1),
                            'bl': self.world.is_solid(gx+1, gy-1, gz-1),
                            'br': self.world.is_solid(gx-1, gy-1, gz-1),
                            'tl': self.world.is_solid(gx+1, gy+1, gz-1),
                            'tr': self.world.is_solid(gx-1, gy+1, gz-1)
                        }
                        ao = [
                            self.calculate_ao(n['t'], n['l'], n['tl']),
                            self.calculate_ao(n['b'], n['l'], n['bl']),
                            self.calculate_ao(n['b'], n['r'], n['br']),
                            self.calculate_ao(n['t'], n['r'], n['tr'])
                        ]
                        e0 = self.calculate_ao_enhanced(gx + 0, gy + 1, gz + 0)
                        e1 = self.calculate_ao_enhanced(gx + 0, gy + 0, gz + 0)
                        e2 = self.calculate_ao_enhanced(gx + 1, gy + 0, gz + 0)
                        e3 = self.calculate_ao_enhanced(gx + 1, gy + 1, gz + 0)
                        fa0 = min(ao[0], e0)
                        fa1 = min(ao[1], e1)
                        fa2 = min(ao[2], e2)
                        fa3 = min(ao[3], e3)
                        v = [
                            ((x, y+1, z),   (0,0,-1), block_type, fa0),
                            ((x, y, z),     (0,0,-1), block_type, fa1),
                            ((x+1, y, z),   (0,0,-1), block_type, fa2),
                            ((x+1, y+1, z), (0,0,-1), block_type, fa3)
                        ]
                        vertex_list.extend(v)
                        i = vertex_index_counter
                        s1 = fa0 + fa2
                        s2 = fa1 + fa3
                        if s1 > s2:
                            index_list.extend([i, i+1, i+2, i, i+2, i+3])
                        elif s1 < s2:
                            index_list.extend([i, i+1, i+3, i+3, i+1, i+2])
                        else:
                            if ((gx + gy + gz) & 1):
                                index_list.extend([i, i+1, i+2, i, i+2, i+3])
                            else:
                                index_list.extend([i, i+1, i+3, i+3, i+1, i+2])
                        vertex_index_counter += 4

                    # --- ✨ FIN DE LA CORRECCIÓN ✨ ---

        if not vertex_list:
            if self.mesh:
                self.mesh.destroy()
            self.mesh = None
            return

        # Ahora la conversión a np.array funcionará correctamente
        vertices = np.array(vertex_list, dtype=data_type_vertex)
        indices = np.array(index_list, dtype=np.uint32)
        
        if self.mesh:
            self.mesh.destroy()
        self.mesh = Mesh(vertices, indices)