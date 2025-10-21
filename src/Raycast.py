# Raycast.py
import numpy as np

class Raycast:
    def __init__(self, world, origin, direction, max_distance=50.0):
        self.world = world
        self.ray_origin = origin.copy()
        self.ray_direction = direction.copy()
        # Debug flag to enable verbose intersection logging
        self.debug = False
        epsilon = 1e-6
        # Evitar división por cero
        if abs(self.ray_direction[1]) < epsilon:
            self.ray_direction[1] = np.sign(self.ray_direction[1]) * epsilon if self.ray_direction[1] != 0 else epsilon
            
        self.max_distance = max_distance
        self.voxel_pos = np.floor(self.ray_origin).astype(int)
        self.step = np.sign(self.ray_direction).astype(int)
        self.delta_dist = np.abs(1.0 / self.ray_direction)

        # Inicialización de side_dist (sin cambios)
        if self.ray_direction[0] < 0: self.side_dist_x = (self.ray_origin[0] - self.voxel_pos[0]) * self.delta_dist[0]
        else: self.side_dist_x = (self.voxel_pos[0] + 1 - self.ray_origin[0]) * self.delta_dist[0]
        if self.ray_direction[1] < 0: self.side_dist_y = (self.ray_origin[1] - self.voxel_pos[1]) * self.delta_dist[1]
        else: self.side_dist_y = (self.voxel_pos[1] + 1 - self.ray_origin[1]) * self.delta_dist[1]
        if self.ray_direction[2] < 0: self.side_dist_z = (self.ray_origin[2] - self.voxel_pos[2]) * self.delta_dist[2]
        else: self.side_dist_z = (self.voxel_pos[2] + 1 - self.ray_origin[2]) * self.delta_dist[2]
            
    def step_forward(self):
        last_voxel_pos = self.voxel_pos.copy()

        # Bucle principal del raycast
        while np.linalg.norm(self.voxel_pos - self.ray_origin) < self.max_distance:
            if self.side_dist_x < self.side_dist_y and self.side_dist_x < self.side_dist_z:
                self.side_dist_x += self.delta_dist[0]
                self.voxel_pos[0] += self.step[0]
                last_voxel_pos = self.voxel_pos.copy(); last_voxel_pos[0] -= self.step[0]
            elif self.side_dist_y < self.side_dist_z:
                self.side_dist_y += self.delta_dist[1]
                self.voxel_pos[1] += self.step[1]
                last_voxel_pos = self.voxel_pos.copy(); last_voxel_pos[1] -= self.step[1]
            else:
                self.side_dist_z += self.delta_dist[2]
                self.voxel_pos[2] += self.step[2]
                last_voxel_pos = self.voxel_pos.copy(); last_voxel_pos[2] -= self.step[2]
            
            # Comprobación de colisión con un bloque existente
            if self.world.is_solid(self.voxel_pos[0], self.voxel_pos[1], self.voxel_pos[2]):
                return tuple(self.voxel_pos), tuple(last_voxel_pos)
        
        # --- INICIO DE LA CORRECCIÓN ---
        # Si el bucle termina sin colisión, intentamos intersectar el rayo
        # con el volumen de la cuadrícula (AABB) para permitir colocar
        # bloques en cualquiera de las seis caras del grid box.

        # Construimos los límites del mundo según World
        world_x = self.world.chunk_size * self.world.world_size_in_chunks
        world_y = self.world.chunk_size
        world_z = world_x

        origin = self.ray_origin
        dir = self.ray_direction
        dir_norm = np.linalg.norm(dir)

        candidates = []

        # Helper to test a plane at coord 'c' on axis 'axis' (0=x,1=y,2=z)
        def test_plane(axis, c):
            # Avoid division by zero
            if abs(dir[axis]) < 1e-8:
                return None
            t = (c - origin[axis]) / dir[axis]
            if t <= 1e-6:
                return None
            # check distance
            if t * dir_norm > self.max_distance:
                return None
            pt = origin + t * dir
            # check the other two coordinates are inside bounds
            if axis == 0:
                y, z = pt[1], pt[2]
                if 0.0 <= y <= world_y and 0.0 <= z <= world_z:
                    return (t, pt)
            elif axis == 1:
                x, z = pt[0], pt[2]
                if 0.0 <= x <= world_x and 0.0 <= z <= world_z:
                    return (t, pt)
            else:
                x, y = pt[0], pt[1]
                if 0.0 <= x <= world_x and 0.0 <= y <= world_y:
                    return (t, pt)
            return None

        # Test all six faces: x=0, x=world_x, y=0, y=world_y, z=0, z=world_z
        planes = [ (0, 0.0), (0, float(world_x)), (1, 0.0), (1, float(world_y)), (2, 0.0), (2, float(world_z)) ]
        for axis, coord in planes:
            res = test_plane(axis, coord)
            if res:
                candidates.append((res[0], axis, coord, res[1]))

        if candidates:
            # Choose the nearest intersection
            candidates.sort(key=lambda x: x[0])
            t, axis, coord, intersection_point = candidates[0]
            ix = int(np.floor(intersection_point[0]))
            iy = int(np.floor(intersection_point[1]))
            iz = int(np.floor(intersection_point[2]))

            # Determine outward normal and place/hit positions
            if axis == 0:
                if coord == 0.0:
                    # Left face: place at x=0, hit at x=-1
                    place_pos = (0, iy, iz)
                    hit_pos = (-1, iy, iz)
                else:
                    # Right face: place at x=world_x-1, hit at x=world_x
                    place_pos = (int(world_x) - 1, iy, iz)
                    hit_pos = (int(world_x), iy, iz)
            elif axis == 1:
                if coord == 0.0:
                    # Bottom: place at y=0, hit below
                    place_pos = (ix, 0, iz)
                    hit_pos = (ix, -1, iz)
                else:
                    # Top: place at y=world_y-1, hit above
                    place_pos = (ix, int(world_y) - 1, iz)
                    hit_pos = (ix, int(world_y), iz)
            else:
                if coord == 0.0:
                    # Back (z=0)
                    place_pos = (ix, iy, 0)
                    hit_pos = (ix, iy, -1)
                else:
                    # Front (z=world_z)
                    place_pos = (ix, iy, int(world_z) - 1)
                    hit_pos = (ix, iy, int(world_z))

            return hit_pos, place_pos
        # Si no hay colisión ni intersección con el volumen del grid, no devolver nada.
        return None, None