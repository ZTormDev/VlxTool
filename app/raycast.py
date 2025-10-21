import math
import numpy as np
import imgui  # type: ignore
import glfw
from typing import cast, Tuple
from src.core.Raycast import Raycast


def update_raycast(app):
    try:
        io = imgui.get_io()  # type: ignore[attr-defined]
        if io.want_capture_mouse:
            app.hit_voxel_pos = None
            return
    except Exception:
        pass

    if getattr(app, 'middle_button_down', False) or getattr(app, 'right_button_down', False):
        app.hit_voxel_pos = None
        app.place_voxel_pos = None
        app.hit_voxel_normal = None
        return

    w, h = glfw.get_window_size(app.window)
    try:
        mx, my = glfw.get_cursor_pos(app.window)
    except Exception:
        mx, my = w / 2.0, h / 2.0

    if mx is None or my is None or mx != mx or my != my:
        mx, my = w / 2.0, h / 2.0
        
    print(f"Cursor pos: mx={mx}, my={my}, w={w}, h={h}")

    ndc_x = (2.0 * mx) / float(w) - 1.0
    ndc_y = 1.0 - (2.0 * my) / float(h)

    cam_front = np.array(app.camera.front, dtype=np.float64)
    cam_right = np.array(app.camera.right, dtype=np.float64)
    cam_up = np.array(app.camera.up, dtype=np.float64)
    fov_y = math.radians(75.0)
    aspect = float(w) / float(h) if h != 0 else 1.0
    tan_y = math.tan(fov_y / 2.0)
    tan_x = tan_y * aspect

    x_camera = ndc_x * tan_x
    y_camera = ndc_y * tan_y
    world_dir = cam_front + cam_right * x_camera + cam_up * y_camera
    world_dir = np.array(world_dir, dtype=np.float32)
    norm = np.linalg.norm(world_dir)
    if norm == 0:
        world_dir = np.array(app.camera.front, dtype=np.float32)
    else:
        world_dir = world_dir / norm

    origin = np.array(app.camera.position, dtype=np.float32)
    ray = Raycast(app.scene.world, origin, world_dir)
    hit, place = ray.step_forward()

    if hit:
        # Decide whether this hit came from an actual voxel inside the
        # world (world collision) or from intersecting the world AABB
        # (grid face). For pivot-setting we want the voxel position when
        # the ray hit a voxel inside the world, not the adjacent "place"
        # position in front of the face.
        is_world_hit = False
        try:
            h = tuple(map(int, hit))
            total = getattr(app.scene.world, 'total_size', None)
            if total is None:
                # If world doesn't expose total_size, assume it's a world hit
                is_world_hit = True
            else:
                # world hit if hit coords are inside [0, total_size-1]
                is_world_hit = (0 <= h[0] < total and 0 <= h[1] < total and 0 <= h[2] < total)
        except Exception:
            is_world_hit = False

        if getattr(app, 'waiting_for_pivot', False) and is_world_hit:
            # Use the actual voxel position for pivot placement
            app.hit_voxel_pos = hit
            app.place_voxel_pos = hit
        else:
            app.hit_voxel_pos, app.place_voxel_pos = hit, place

        # Compute normal robustly: prefer (place - hit) when both exist,
        # otherwise default to zero vector.
        try:
            p = cast(Tuple[int, int, int], place if place is not None else hit)
            h = cast(Tuple[int, int, int], hit)
            app.hit_voxel_normal = (p[0] - h[0], p[1] - h[1], p[2] - h[2])
        except Exception:
            app.hit_voxel_normal = (0, 0, 0)
    else:
        app.hit_voxel_pos, app.place_voxel_pos, app.hit_voxel_normal = None, None, None


def face_name_from_normal(n):
    if not n:
        return "None"
    x, y, z = n
    if y > 0.9:
        return "Top (+Y)"
    if y < -0.9:
        return "Bottom (-Y)"
    if x > 0.9:
        return "Right (+X)"
    if x < -0.9:
        return "Left (-X)"
    if z > 0.9:
        return "Front (+Z)"
    if z < -0.9:
        return "Back (-Z)"
    return f"({x:.2f},{y:.2f},{z:.2f})"
