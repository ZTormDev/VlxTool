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

        self.clear_world()
        try:
            with open(filepath, 'r') as f:
                for line in f:
                    if not line.strip() or line.startswith('#'): continue
                    parts = line.split()
                    if parts[0] == 'VOXEL' and len(parts) == 5:
                        fx, fy, fz, block_id = map(int, parts[1:])
                        ex, ey, ez = fx, fz, fy
                        try:
                            self.world.set_voxel(ex, ey, ez, self.BlockType(block_id))
                        except ValueError:
                            print(f"Warning: Unknown block ID '{block_id}'. Skipping.")
                    elif parts[0] == 'PIVOT' and len(parts) == 4:
                        try:
                            px, py, pz = map(int, parts[1:])
                            self.world.pivot = (px, py, pz)
                        except Exception:
                            pass
            print(f"World loaded from {filepath}")
            self.history_manager.add_entry(filepath)
            return filepath
        except Exception as e:
            print(f"Error loading file: {e}")
            return None