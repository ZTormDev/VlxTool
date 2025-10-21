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
        Improved Ambient Occlusion calculation.

        side1, side2, corner are truthy values (0/1 or bool). We compute a
        higher-quality AO value by:
        - computing the normalized un-occluded amount (raw)
        - applying a mild ease (square) to increase contrast smoothly
        - remapping into a comfortable range so faces never go fully black

        Returns a float in roughly [0.35, 1.0].
        """
        # normalize inputs to 0/1 integers
        s = 1 if side1 else 0
        t = 1 if side2 else 0
        c = 1 if corner else 0

        # Standard voxel AO rule:
        # - adjacent sides (s and t) each contribute 1 when occupied
        # - the corner only contributes if BOTH adjacent sides are occupied
        # This prevents the corner from darkening a vertex when it's isolated
        # (which looks visually incorrect).
        corner_contrib = c if (s and t) else 0
        occlusion_count = s + t + corner_contrib  # 0..3

        # raw: 1.0 = fully open, 0.0 = fully occluded
        raw = 1.0 - (occlusion_count / 3.0)

        # apply a mild ease to make AO darker where there is more occlusion
        eased = raw * raw

        # keep AO in a non-extreme range so lighting doesn't go fully black;
        # tweak `min_ao` to control darkness strength
        min_ao = 0.35
        ao = min_ao + eased * (1.0 - min_ao)

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
                        n = {'b':self.world.is_solid(gx+1,gy-1,gz), 't':self.world.is_solid(gx+1,gy+1,gz), 'l':self.world.is_solid(gx+1,gy,gz-1), 'r':self.world.is_solid(gx+1,gy,gz+1), 'bl':self.world.is_solid(gx+1,gy-1,gz-1), 'br':self.world.is_solid(gx+1,gy-1,gz+1), 'tl':self.world.is_solid(gx+1,gy+1,gz-1), 'tr':self.world.is_solid(gx+1,gy+1,gz+1)}
                        ao = [self.calculate_ao(n['t'], n['l'], n['tl']), self.calculate_ao(n['b'], n['l'], n['bl']), self.calculate_ao(n['b'], n['r'], n['br']), self.calculate_ao(n['t'], n['r'], n['tr'])]
                        v = [((x+1, y+1, z),   (1,0,0), block_type, ao[0]), 
                             ((x+1, y, z),     (1,0,0), block_type, ao[1]), 
                             ((x+1, y, z+1),   (1,0,0), block_type, ao[2]), 
                             ((x+1, y+1, z+1), (1,0,0), block_type, ao[3])]
                        vertex_list.extend(v); i = vertex_index_counter
                        if ao[0]+ao[2]>ao[1]+ao[3]: index_list.extend([i,i+1,i+2,i,i+2,i+3])
                        else: index_list.extend([i,i+1,i+3,i+3,i+1,i+2])
                        vertex_index_counter += 4
                    
                    # Cara -X (Izquierda)
                    if not self.world.is_solid(gx - 1, gy, gz):
                        n = {'b':self.world.is_solid(gx-1,gy-1,gz), 't':self.world.is_solid(gx-1,gy+1,gz), 'l':self.world.is_solid(gx-1,gy,gz+1), 'r':self.world.is_solid(gx-1,gy,gz-1), 'bl':self.world.is_solid(gx-1,gy-1,gz+1), 'br':self.world.is_solid(gx-1,gy-1,gz-1), 'tl':self.world.is_solid(gx-1,gy+1,gz+1), 'tr':self.world.is_solid(gx-1,gy+1,gz-1)}
                        ao = [self.calculate_ao(n['t'], n['l'], n['tl']), self.calculate_ao(n['b'], n['l'], n['bl']), self.calculate_ao(n['b'], n['r'], n['br']), self.calculate_ao(n['t'], n['r'], n['tr'])]
                        v = [((x, y+1, z+1), (-1,0,0), block_type, ao[0]), 
                             ((x, y, z+1),   (-1,0,0), block_type, ao[1]), 
                             ((x, y, z),     (-1,0,0), block_type, ao[2]), 
                             ((x, y+1, z),   (-1,0,0), block_type, ao[3])]
                        vertex_list.extend(v); i = vertex_index_counter
                        if ao[0]+ao[2]>ao[1]+ao[3]: index_list.extend([i,i+1,i+2,i,i+2,i+3])
                        else: index_list.extend([i,i+1,i+3,i+3,i+1,i+2])
                        vertex_index_counter += 4

                    # Cara +Y (Arriba)
                    if not self.world.is_solid(gx, gy + 1, gz):
                        n = {'b':self.world.is_solid(gx,gy+1,gz-1), 't':self.world.is_solid(gx,gy+1,gz+1), 'l':self.world.is_solid(gx-1,gy+1,gz), 'r':self.world.is_solid(gx+1,gy+1,gz), 'bl':self.world.is_solid(gx-1,gy+1,gz-1), 'br':self.world.is_solid(gx+1,gy+1,gz-1), 'tl':self.world.is_solid(gx-1,gy+1,gz+1), 'tr':self.world.is_solid(gx+1,gy+1,gz+1)}
                        ao = [self.calculate_ao(n['t'], n['l'], n['tl']), self.calculate_ao(n['b'], n['l'], n['bl']), self.calculate_ao(n['b'], n['r'], n['br']), self.calculate_ao(n['t'], n['r'], n['tr'])]
                        v = [((x, y+1, z+1),   (0,1,0), block_type, ao[0]), 
                             ((x, y+1, z),     (0,1,0), block_type, ao[1]), 
                             ((x+1, y+1, z),   (0,1,0), block_type, ao[2]), 
                             ((x+1, y+1, z+1), (0,1,0), block_type, ao[3])]
                        vertex_list.extend(v); i = vertex_index_counter
                        if ao[0]+ao[2]>ao[1]+ao[3]: index_list.extend([i,i+1,i+2,i,i+2,i+3])
                        else: index_list.extend([i,i+1,i+3,i+3,i+1,i+2])
                        vertex_index_counter += 4

                    # Cara -Y (Abajo)
                    if not self.world.is_solid(gx, gy - 1, gz):
                        n = {'b':self.world.is_solid(gx,gy-1,gz-1), 't':self.world.is_solid(gx,gy-1,gz+1), 'l':self.world.is_solid(gx-1,gy-1,gz), 'r':self.world.is_solid(gx+1,gy-1,gz), 'bl':self.world.is_solid(gx-1,gy-1,gz-1), 'br':self.world.is_solid(gx+1,gy-1,gz-1), 'tl':self.world.is_solid(gx-1,gy-1,gz+1), 'tr':self.world.is_solid(gx+1,gy-1,gz+1)}
                        ao = [self.calculate_ao(n['t'], n['r'], n['tr']), self.calculate_ao(n['b'], n['r'], n['br']), self.calculate_ao(n['b'], n['l'], n['bl']), self.calculate_ao(n['t'], n['l'], n['tl'])]
                        v = [((x+1, y, z+1), (0,-1,0), block_type, ao[0]), 
                             ((x+1, y, z),   (0,-1,0), block_type, ao[1]), 
                             ((x, y, z),     (0,-1,0), block_type, ao[2]), 
                             ((x, y, z+1),   (0,-1,0), block_type, ao[3])]
                        vertex_list.extend(v); i = vertex_index_counter
                        if ao[0]+ao[2]>ao[1]+ao[3]: index_list.extend([i,i+1,i+2,i,i+2,i+3])
                        else: index_list.extend([i,i+1,i+3,i+3,i+1,i+2])
                        vertex_index_counter += 4

                    # Cara +Z (Frente)
                    if not self.world.is_solid(gx, gy, gz + 1):
                        n = {'b':self.world.is_solid(gx,gy-1,gz+1), 't':self.world.is_solid(gx,gy+1,gz+1), 'l':self.world.is_solid(gx-1,gy,gz+1), 'r':self.world.is_solid(gx+1,gy,gz+1), 'bl':self.world.is_solid(gx-1,gy-1,gz+1), 'br':self.world.is_solid(gx+1,gy-1,gz+1), 'tl':self.world.is_solid(gx-1,gy+1,gz+1), 'tr':self.world.is_solid(gx+1,gy+1,gz+1)}
                        ao = [self.calculate_ao(n['t'], n['r'], n['tr']), self.calculate_ao(n['b'], n['r'], n['br']), self.calculate_ao(n['b'], n['l'], n['bl']), self.calculate_ao(n['t'], n['l'], n['tl'])]
                        v = [((x+1, y+1, z+1), (0,0,1), block_type, ao[0]), 
                             ((x+1, y, z+1),   (0,0,1), block_type, ao[1]), 
                             ((x, y, z+1),     (0,0,1), block_type, ao[2]), 
                             ((x, y+1, z+1),   (0,0,1), block_type, ao[3])]
                        vertex_list.extend(v); i = vertex_index_counter
                        if ao[0]+ao[2]>ao[1]+ao[3]: index_list.extend([i,i+1,i+2,i,i+2,i+3])
                        else: index_list.extend([i,i+1,i+3,i+3,i+1,i+2])
                        vertex_index_counter += 4

                    # Cara -Z (Atrás)
                    if not self.world.is_solid(gx, gy, gz - 1):
                        n = {'b':self.world.is_solid(gx,gy-1,gz-1), 't':self.world.is_solid(gx,gy+1,gz-1), 'l':self.world.is_solid(gx+1,gy,gz-1), 'r':self.world.is_solid(gx-1,gy,gz-1), 'bl':self.world.is_solid(gx+1,gy-1,gz-1), 'br':self.world.is_solid(gx-1,gy-1,gz-1), 'tl':self.world.is_solid(gx+1,gy+1,gz-1), 'tr':self.world.is_solid(gx-1,gy+1,gz-1)}
                        ao = [self.calculate_ao(n['t'], n['l'], n['tl']), self.calculate_ao(n['b'], n['l'], n['bl']), self.calculate_ao(n['b'], n['r'], n['br']), self.calculate_ao(n['t'], n['r'], n['tr'])]
                        # Invert vertex order for back face so winding is correct
                        v = [((x, y+1, z),   (0,0,-1), block_type, ao[0]),
                             ((x, y, z),     (0,0,-1), block_type, ao[1]),
                             ((x+1, y, z),   (0,0,-1), block_type, ao[2]),
                             ((x+1, y+1, z), (0,0,-1), block_type, ao[3])]
                        vertex_list.extend(v); i = vertex_index_counter
                        if ao[0]+ao[2]>ao[1]+ao[3]:
                            index_list.extend([i,i+1,i+2,i,i+2,i+3])
                        else:
                            index_list.extend([i,i+1,i+3,i+3,i+1,i+2])
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