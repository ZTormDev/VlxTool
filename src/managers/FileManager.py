# src/FileManager.py
import os
import numpy as np
from tkinter import Tk, filedialog

class FileManager:
    def __init__(self, world, block_type_enum, history_manager):
        self.world = world
        self.BlockType = block_type_enum
        self.history_manager = history_manager

    def clear_world(self):
        for chunk in self.world.chunks.values():
            chunk.voxels.fill(self.BlockType.Air.value)
            self.world.dirty_chunks.add(chunk)
        print("World cleared.")

    def save_world(self):
        root = Tk(); root.withdraw()
        filepath = filedialog.asksaveasfilename(defaultextension=".vlx", filetypes=[("Voxeland Model", "*.vlx")], title="Save Voxeland Model")
        root.destroy()
        if not filepath: return None

        min_coords, max_coords, voxel_data, has_voxels = np.array([np.inf]*3), np.array([-np.inf]*3), [], False
        for chunk in self.world.chunks.values():
            non_air = np.argwhere(chunk.voxels != self.BlockType.Air.value)
            if non_air.size == 0: continue
            has_voxels = True
            for x, y, z in non_air:
                block_id = chunk.voxels[x, y, z]
                gx, gy, gz = chunk.get_global_pos(x, y, z)
                rot_gx, rot_gy, rot_gz = gx, gz, gy
                min_coords = np.minimum(min_coords, [rot_gx, rot_gy, rot_gz])
                max_coords = np.maximum(max_coords, [rot_gx, rot_gy, rot_gz])
                voxel_data.append((rot_gx, rot_gy, rot_gz, int(block_id)))
        
        try:
            # If a pivot exists, include it in the AABB calculation. The file
            # format swaps Y and Z when writing, so apply the same rotation to
            # the pivot when comparing with min/max.
            pivot_included = False
            try:
                if hasattr(self.world, 'pivot') and self.world.pivot is not None:
                    px, py, pz = map(int, self.world.pivot)
                    rot_pivot = np.array([px, pz, py], dtype=np.float64)
                    if has_voxels:
                        min_coords = np.minimum(min_coords, rot_pivot)
                        max_coords = np.maximum(max_coords, rot_pivot)
                    else:
                        # No voxels at all; pivot defines the AABB
                        min_coords = np.minimum(min_coords, rot_pivot)
                        max_coords = np.maximum(max_coords, rot_pivot)
                    pivot_included = True
            except Exception:
                pivot_included = False

            with open(filepath, 'w') as f:
                f.write("# Voxeland Model Format v1.0\n")
                if has_voxels or pivot_included:
                    aabb = " ".join(map(str, np.round(np.concatenate((min_coords, max_coords)))))
                else:
                    aabb = "0 0 0 0 0 0"
                f.write(f"AABB {aabb}\n")
                # Save pivot information (world-space voxel integer coordinates)
                try:
                    if hasattr(self.world, 'pivot') and self.world.pivot is not None:
                        px, py, pz = self.world.pivot
                        f.write(f"PIVOT {int(px)} {int(py)} {int(pz)}\n")
                    else:
                        f.write("PIVOT 0 0 0\n")
                except Exception:
                    f.write("PIVOT 0 0 0\n")
                f.write("# VOXELS: x y z block_type_id\n")
                for data in voxel_data: f.write(f"VOXEL {data[0]} {data[1]} {data[2]} {data[3]}\n")
            print(f"World saved to {filepath} with Y-Z axis swapped.")
            self.history_manager.add_entry(filepath)
            return filepath
        except Exception as e:
            print(f"Error saving file: {e}")
            return None

    def load_world(self):
        root = Tk(); root.withdraw()
        filepath = filedialog.askopenfilename(filetypes=[("Voxeland Model", "*.vlx")], title="Load Voxeland Model")
        root.destroy()
        if not filepath: return None
        return self.load_world_from_path(filepath)

    def load_world_from_path(self, filepath):
        if not os.path.exists(filepath):
            print(f"Error: File not found at '{filepath}'. Removing from history.")
            self.history_manager.remove_entry(filepath)
            return None
        # Read file first and collect voxel entries so we can compute AABB and
        # derive a translation that centers the model horizontally and places
        # its bottom at y=0 (center-bottom of the editor).
        self.clear_world()
        try:
            voxels = []  # list of (x,y,z,block_id) in world/global coords
            file_pivot = None
            with open(filepath, 'r') as f:
                for line in f:
                    if not line.strip() or line.startswith('#'):
                        continue
                    parts = line.split()
                    if parts[0] == 'VOXEL' and len(parts) == 5:
                        fx, fy, fz, block_id = map(int, parts[1:])
                        # The file format swaps Y and Z when writing; apply same
                        # rotation when reading (file: fx,fy,fz -> world: x=fx, y=fz, z=fy)
                        ex, ey, ez = fx, fz, fy
                        voxels.append((ex, ey, ez, int(block_id)))
                    elif parts[0] == 'PIVOT' and len(parts) == 4:
                        try:
                            px, py, pz = map(int, parts[1:])
                            file_pivot = (px, py, pz)
                        except Exception:
                            file_pivot = None

            if not voxels and file_pivot is None:
                # Nothing to place; still register history and return
                print(f"World loaded from {filepath} (empty)")
                self.history_manager.add_entry(filepath)
                return filepath

            # Compute AABB from collected voxels (and include pivot if present)
            import numpy as _np
            coords = _np.array([[v[0], v[1], v[2]] for v in voxels], dtype=_np.int64) if voxels else _np.zeros((0,3), dtype=_np.int64)
            if file_pivot is not None:
                # Include pivot in AABB calculation
                px, py, pz = file_pivot
                pivot_arr = _np.array([[int(px), int(py), int(pz)]], dtype=_np.int64)
                coords = _np.vstack([coords, pivot_arr]) if coords.size else pivot_arr

            min_coords = coords.min(axis=0) if coords.size else _np.array([0,0,0], dtype=_np.int64)
            max_coords = coords.max(axis=0) if coords.size else _np.array([0,0,0], dtype=_np.int64)

            # Determine translation: center model X/Z to world center, place model bottom at y=0
            world_size = getattr(self.world, 'total_size', None)
            if world_size is None:
                world_size = getattr(self.world, 'base_chunk_size', 32) * getattr(self.world, 'world_size_in_chunks', 2)

            # Use integer world center
            world_center = _np.array([world_size // 2, 0, world_size // 2], dtype=_np.int64)

            model_center_xz = _np.array([(min_coords[0] + max_coords[0]) / 2.0, (min_coords[2] + max_coords[2]) / 2.0])
            # translation x and z to place model center at world center
            tx = int(round(world_center[0] - model_center_xz[0]))
            tz = int(round(world_center[2] - model_center_xz[1]))
            # translation y to move min_y to 0 (bring bottom to y=0)
            ty = int(-min_coords[1])

            # Apply tentative translation and ensure the translated AABB fits inside the world
            translated_min = min_coords + _np.array([tx, ty, tz], dtype=_np.int64)
            translated_max = max_coords + _np.array([tx, ty, tz], dtype=_np.int64)

            # If out of bounds, shift to fit within [0, world_size-1]
            adjust = _np.array([0,0,0], dtype=_np.int64)
            if translated_min[0] < 0:
                adjust[0] = -translated_min[0]
            if translated_min[1] < 0:
                adjust[1] = -translated_min[1]
            if translated_min[2] < 0:
                adjust[2] = -translated_min[2]
            if translated_max[0] >= world_size:
                adjust[0] = min(adjust[0], world_size - 1 - translated_max[0])
            if translated_max[1] >= world_size:
                adjust[1] = min(adjust[1], world_size - 1 - translated_max[1])
            if translated_max[2] >= world_size:
                adjust[2] = min(adjust[2], world_size - 1 - translated_max[2])

            tx += int(adjust[0]); ty += int(adjust[1]); tz += int(adjust[2])

            # Place voxels with applied translation
            for ex, ey, ez, block_id in voxels:
                nx = int(ex + tx); ny = int(ey + ty); nz = int(ez + tz)
                # Bounds check to be defensive
                if not (0 <= nx < world_size and 0 <= ny < world_size and 0 <= nz < world_size):
                    # Skip voxels that still fall outside the world after adjustment
                    continue
                try:
                    self.world.set_voxel(nx, ny, nz, self.BlockType(block_id))
                except ValueError:
                    print(f"Warning: Unknown block ID '{block_id}'. Skipping.")

            # Translate and set pivot if present
            if file_pivot is not None:
                px, py, pz = file_pivot
                new_px = int(px + tx); new_py = int(py + ty); new_pz = int(pz + tz)
                # Clamp pivot inside world
                new_px = max(0, min(world_size - 1, new_px))
                new_py = max(0, min(world_size - 1, new_py))
                new_pz = max(0, min(world_size - 1, new_pz))
                self.world.pivot = (new_px, new_py, new_pz)

            print(f"World loaded from {filepath}")
            self.history_manager.add_entry(filepath)
            return filepath
        except Exception as e:
            print(f"Error loading file: {e}")
            return None