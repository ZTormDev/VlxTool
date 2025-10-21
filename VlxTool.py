# VlxTool.py
import os
import sys
import numpy as np
import pyrr
import glfw
import imgui  # type: ignore
import math
from typing import cast, Tuple

from OpenGL.GL import (
    glClear,
    glEnable,
    glCullFace,
    glFrontFace,
    glDeleteProgram,
    glClearColor,
    GL_COLOR_BUFFER_BIT,
    GL_DEPTH_BUFFER_BIT,
    GL_DEPTH_TEST,
    GL_CULL_FACE,
    GL_BACK,
    GL_CW,
)
from tkinter import Tk, filedialog

# Importaciones de los módulos del proyecto
from src.core.Camera import Camera
from src.core.Scene import Scene
from src.utils.Config import SCREEN_WIDTH, SCREEN_HEIGHT, create_shader_program
from src.utils.BlockTypes import load_from_hpp
from src.core.Raycast import Raycast
from src.managers.SettingsManager import SettingsManager
from src.managers.HistoryManager import HistoryManager
from src.managers.FileManager import FileManager
from src.managers.UIManager import UIManager

# Constantes de GLFW para mayor claridad
from glfw.GLFW import (
    GLFW_CONTEXT_VERSION_MAJOR, GLFW_CONTEXT_VERSION_MINOR,
    GLFW_OPENGL_PROFILE, GLFW_OPENGL_CORE_PROFILE,
    GLFW_OPENGL_FORWARD_COMPAT, GLFW_TRUE,
    GLFW_CURSOR, GLFW_CURSOR_DISABLED, GLFW_CURSOR_NORMAL,
    GLFW_KEY_LEFT_ALT, GLFW_KEY_ESCAPE, GLFW_KEY_LEFT_SHIFT,
    GLFW_KEY_W, GLFW_KEY_S, GLFW_KEY_A, GLFW_KEY_D,
    GLFW_KEY_SPACE, GLFW_KEY_LEFT_CONTROL, GLFW_PRESS
)

class App:
    def __init__(self):
        # --- Inicialización de Gestores y Configuración ---
        self.settings_manager = SettingsManager()
        self.history_manager = HistoryManager(self.settings_manager.settings_dir)

        settings = self.settings_manager.load_settings()
        hpp_path = settings.get('hpp_path') if settings else None
        if not hpp_path:
            hpp_path = self.prompt_for_hpp_file()
            if hpp_path:
                self.settings_manager.save_settings({'hpp_path': hpp_path})
        if not hpp_path:
            sys.exit("No .hpp file selected.")

        # --- Inicialización de Componentes Gráficos y del Mundo ---
        self.initialize_glfw()
        self.BlockType, self.BLOCK_COLORS = load_from_hpp(hpp_path)
        imgui.create_context()  # type: ignore[attr-defined]

        # La clase Scene ahora se encarga de crear el mundo, la rejilla, etc.
        self.scene = Scene(self.BlockType, self.BLOCK_COLORS)

        self.camera = self.initialize_camera()

        # --- Inicialización de Gestores Dependientes ---
        self.file_manager = FileManager(self.scene.world, self.BlockType, self.history_manager)
        self.ui_manager = UIManager(self.window, self)

        # --- Estado de la Aplicación ---
        # Keep cursor visible by default. We'll hide & center it only while
        # the user is actively rotating (right) or panning (middle).
        self.is_mouse_captured = True
        # For orbit/pan controls when mouse is released
        self.last_cursor_pos = None
        self.middle_button_down = False
        self.right_button_down = False
        # Flag used to ignore the first cursor delta after we programmatically
        # center the cursor to avoid a large jump in camera movement.
        self.just_centered = False
        # Disable keyboard movement by default (MagicaVoxel-like)
        self.enable_keyboard_movement = False
        self.alt_pressed_last_frame = False
        self.hit_voxel_pos, self.place_voxel_pos, self.hit_voxel_normal = None, None, None
        self.current_filepath = None

        # Build placeable blocks defensively. BlockType may be a dynamic Enum type.
        members = getattr(self.BlockType, '__members__', None)
        if isinstance(members, dict):
            # __members__ preserves declaration order
            self.placeable_blocks = [getattr(self.BlockType, name) for name in members if name != 'Air']
        else:
            # Fallback: attempt to get an iterator at runtime; silence the type-checker
            try:
                iterator = iter(self.BlockType)  # type: ignore[arg-type]
            except Exception:
                self.placeable_blocks = []
            else:
                self.placeable_blocks = [bt for bt in iterator if getattr(bt, 'name', None) != 'Air']

        self.active_block_type = self.placeable_blocks[0] if self.placeable_blocks else None

        self.initialize_opengl()
        self.set_callbacks()

    def initialize_glfw(self):
        if not glfw.init(): sys.exit("Could not initialize GLFW")
        glfw.window_hint(GLFW_CONTEXT_VERSION_MAJOR, 3); glfw.window_hint(GLFW_CONTEXT_VERSION_MINOR, 3)
        glfw.window_hint(GLFW_OPENGL_PROFILE, GLFW_OPENGL_CORE_PROFILE); glfw.window_hint(GLFW_OPENGL_FORWARD_COMPAT, GLFW_TRUE)
        self.window = glfw.create_window(SCREEN_WIDTH, SCREEN_HEIGHT, "VlxTool", None, None)
        if not self.window: glfw.terminate(); sys.exit("Could not create window")
        # Start with a normal, visible cursor. Individual mouse-button handlers
        # will hide/center the cursor while the user is interacting.
        glfw.make_context_current(self.window)
        glfw.set_input_mode(self.window, GLFW_CURSOR, GLFW_CURSOR_NORMAL)

    def initialize_camera(self):
        world_coord_size = self.scene.world.chunk_size * self.scene.world.world_size_in_chunks #
        return Camera(
            position=[world_coord_size / 2, world_coord_size / 2 + 10, world_coord_size / 2],
            # default target at world center
            target=[world_coord_size / 2, world_coord_size / 2, world_coord_size / 2]
        ) #

    def set_callbacks(self):
        glfw.set_cursor_pos_callback(self.window, self.mouse_look_callback)
        glfw.set_scroll_callback(self.window, self.scroll_callback)
        glfw.set_mouse_button_callback(self.window, self.mouse_button_callback)
        
    def initialize_opengl(self):
        glClearColor(0.1, 0.2, 0.5, 1); glEnable(GL_DEPTH_TEST); glEnable(GL_CULL_FACE)
        glCullFace(GL_BACK); glFrontFace(GL_CW)
        vert = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shaders", "voxel.vert")
        frag = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shaders", "voxel.frag")
        self.voxel_shader = create_shader_program(vert, frag)
        if not self.voxel_shader: sys.exit("Voxel shader failed to compile.")

    def run(self):
        last_time = glfw.get_time()
        while not glfw.window_should_close(self.window):
            current_time = glfw.get_time()
            delta_time = current_time - last_time
            last_time = current_time
            
            glfw.poll_events()
            self.ui_manager.renderer.process_inputs()
            self.process_input(delta_time)
            self.update_raycast()
            self.scene.world.update_dirty_chunks() #
            
            self.render_frame()
            
            glfw.swap_buffers(self.window)

    def render_frame(self):
        mask = GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT  # type: ignore[arg-type]
        glClear(mask)
        view = self.camera.get_view_matrix() #
        proj = pyrr.matrix44.create_perspective_projection(75, SCREEN_WIDTH/SCREEN_HEIGHT, 0.1, 1024, np.float32)

        # La clase Scene se encarga de toda la lógica de renderizado
        self.scene.render(proj, view, self.voxel_shader, self.hit_voxel_pos, self.hit_voxel_normal) #
        
        self.ui_manager.render_ui() #

    def process_input(self, delta_time):
        if glfw.get_key(self.window, GLFW_KEY_LEFT_ALT) == GLFW_PRESS and not self.alt_pressed_last_frame:
            self.is_mouse_captured = not self.is_mouse_captured
            cursor_mode = GLFW_CURSOR_DISABLED if self.is_mouse_captured else GLFW_CURSOR_NORMAL
            glfw.set_input_mode(self.window, GLFW_CURSOR, cursor_mode)
        self.alt_pressed_last_frame = glfw.get_key(self.window, GLFW_KEY_LEFT_ALT) == GLFW_PRESS

        if glfw.get_key(self.window, GLFW_KEY_ESCAPE) == GLFW_PRESS:
            glfw.set_window_should_close(self.window, True)
        

    def mouse_look_callback(self, window, xpos, ypos):
        # If we just programmatically centered the cursor, ignore the first
        # movement callback to avoid a large spurious delta. This prevents
        # an immediate big jump when starting an orbit/pan.
        if getattr(self, 'just_centered', False):
            self.just_centered = False
            # Update last cursor pos to the current coords and skip movement
            self.last_cursor_pos = (xpos, ypos)
            return
        # If mouse is captured, keep FPS-look behavior, but allow right-button pan
        if self.is_mouse_captured:
            w, h = glfw.get_window_size(window)
            center_x, center_y = w / 2, h / 2
            # Middle mouse (wheel) press + drag -> PAN (move camera position)
            if self.middle_button_down:
                dx = xpos - center_x
                dy = ypos - center_y
                self.camera.pan(dx, dy)
                glfw.set_cursor_pos(window, center_x, center_y)
                return

            # Right mouse press + drag -> ORBIT/ROTATE around target
            if self.right_button_down:
                dx = xpos - center_x
                dy = ypos - center_y
                # invert Y for a natural drag-to-rotate feel
                self.camera.orbit(dx, dy)
                glfw.set_cursor_pos(window, center_x, center_y)
                return

            # If no relevant button is pressed, do not rotate or pan the camera.
            # This ensures movement/looking only happens while holding the configured buttons.
            return

        # If mouse is free, handle orbit/pan when middle button is down
        if self.last_cursor_pos is None:
            self.last_cursor_pos = (xpos, ypos)
            return

        lx, ly = self.last_cursor_pos
        dx, dy = xpos - lx, ypos - ly
        self.last_cursor_pos = (xpos, ypos)

        if self.middle_button_down:
            # Middle mouse (wheel) press + drag -> PAN (move camera position)
            self.camera.pan(dx, dy)
        elif self.right_button_down:
            # Right-click drag -> ORBIT/ROTATE
            self.camera.orbit(dx, dy)

    def scroll_callback(self, window, x_offset, y_offset):
        # Use mouse wheel to zoom camera distance (always)
        self.camera.zoom(y_offset)

    def mouse_button_callback(self, window, button, action, mods):
        # GLFW middle mouse button constant is 2 but use glfw to be safe
        # Forward the event to the UI manager first so UI placement can occur
        try:
            if hasattr(self, 'ui_manager') and self.ui_manager:
                # UIManager will ignore the event if ImGui wants the mouse
                self.ui_manager.on_mouse_button(window, button, action, mods)
        except Exception:
            pass
        if button == glfw.MOUSE_BUTTON_MIDDLE:
            if action == glfw.PRESS:
                self.middle_button_down = True
                # Hide and lock the cursor to the window center while panning
                w, h = glfw.get_window_size(self.window)
                center_x, center_y = w / 2, h / 2
                glfw.set_cursor_pos(self.window, center_x, center_y)
                # Mark that we just centered the cursor so the next movement
                # callback ignores a spurious large delta.
                self.just_centered = True
                glfw.set_input_mode(self.window, GLFW_CURSOR, GLFW_CURSOR_DISABLED)
                self.last_cursor_pos = (center_x, center_y)
            elif action == glfw.RELEASE:
                self.middle_button_down = False
                # Restore visible cursor when done
                glfw.set_input_mode(self.window, GLFW_CURSOR, GLFW_CURSOR_NORMAL)
        elif button == glfw.MOUSE_BUTTON_RIGHT:
            if action == glfw.PRESS:
                self.right_button_down = True
                # Hide and lock the cursor to the window center while orbiting
                w, h = glfw.get_window_size(self.window)
                center_x, center_y = w / 2, h / 2
                glfw.set_cursor_pos(self.window, center_x, center_y)
                # Ignore the first movement event after centering.
                self.just_centered = True
                glfw.set_input_mode(self.window, GLFW_CURSOR, GLFW_CURSOR_DISABLED)
                self.last_cursor_pos = (center_x, center_y)
            elif action == glfw.RELEASE:
                self.right_button_down = False
                # Restore visible cursor when done
                glfw.set_input_mode(self.window, GLFW_CURSOR, GLFW_CURSOR_NORMAL)

    def update_raycast(self):
        # Don't run the world raycast if ImGui is capturing the mouse (e.g. UI interaction)
        try:
            io = imgui.get_io()  # type: ignore[attr-defined]
            if io.want_capture_mouse:
                self.hit_voxel_pos = None
                return
        except Exception:
            # If imgui isn't available for some reason, continue.
            pass

        # Also skip raycast while the user is actively panning or orbiting the camera
        # to avoid flickering/highlighting while moving the view.
        if getattr(self, 'middle_button_down', False) or getattr(self, 'right_button_down', False):
            self.hit_voxel_pos = None
            self.place_voxel_pos = None
            self.hit_voxel_normal = None
            return

        # Compute ray direction using camera basis and cursor position.
        # This uses the camera's rotation (front/right/up) and the current FOV/aspect
        # so the ray matches what you see on screen.
        w, h = glfw.get_window_size(self.window)
        try:
            mx, my = glfw.get_cursor_pos(self.window)
        except Exception:
            mx, my = w / 2.0, h / 2.0

        if mx is None or my is None or mx != mx or my != my:
            mx, my = w / 2.0, h / 2.0

        # Convert to normalized device coords [-1,1]
        ndc_x = (2.0 * mx) / float(w) - 1.0
        ndc_y = 1.0 - (2.0 * my) / float(h)

        # Camera basis
        cam_front = np.array(self.camera.front, dtype=np.float64)
        cam_right = np.array(self.camera.right, dtype=np.float64)
        cam_up = np.array(self.camera.up, dtype=np.float64)

        # Field of view in radians
        fov_y = math.radians(75.0)
        # aspect ratio based on window size (more correct for DPI)
        aspect = float(w) / float(h) if h != 0 else SCREEN_WIDTH / SCREEN_HEIGHT

        # Convert NDC to camera space direction components
        # At the near plane, x_camera = ndc_x * tan(fov_x/2), y_camera = ndc_y * tan(fov_y/2)
        tan_y = math.tan(fov_y / 2.0)
        tan_x = tan_y * aspect

        x_camera = ndc_x * tan_x
        y_camera = ndc_y * tan_y

        # Compose the world-space direction: forward + right * x + up * y
        world_dir = cam_front + cam_right * x_camera + cam_up * y_camera
        world_dir = np.array(world_dir, dtype=np.float32)
        norm = np.linalg.norm(world_dir)
        if norm == 0:
            world_dir = np.array(self.camera.front, dtype=np.float32)
        else:
            world_dir = world_dir / norm

        # Slightly offset origin forward to avoid self-intersection
        origin = np.array(self.camera.position, dtype=np.float32) + world_dir * 0.001
        ray = Raycast(self.scene.world, origin, world_dir)
        hit, place = ray.step_forward()

        if hit:
            self.hit_voxel_pos, self.place_voxel_pos = hit, place
            # cast to Tuple[int,int,int] for the type checker then compute normal
            try:
                p = cast(Tuple[int, int, int], place)
                h = cast(Tuple[int, int, int], hit)
                self.hit_voxel_normal = (p[0] - h[0], p[1] - h[1], p[2] - h[2])
            except Exception:
                self.hit_voxel_normal = (0, 0, 0)
        else:
            # Si no hay hit, reseteamos las posiciones
            self.hit_voxel_pos, self.place_voxel_pos, self.hit_voxel_normal = None, None, None

    def face_name_from_normal(self):
        """Return a human-friendly face name derived from current hit normal."""
        n = self.hit_voxel_normal
        if not n: return "None"
        x, y, z = n
        if y > 0.9: return "Top (+Y)"
        if y < -0.9: return "Bottom (-Y)"
        if x > 0.9: return "Right (+X)"
        if x < -0.9: return "Left (-X)"
        if z > 0.9: return "Front (+Z)"
        if z < -0.9: return "Back (-Z)"
        return f"({x:.2f},{y:.2f},{z:.2f})"

    # --- Funciones de la Aplicación para la UI ---
    def app_save_world(self):
        if path := self.file_manager.save_world(): self.current_filepath = path
    def app_load_world(self):
        if path := self.file_manager.load_world(): self.current_filepath = path
    def app_load_from_history(self, path):
        if loaded_path := self.file_manager.load_world_from_path(path): self.current_filepath = loaded_path
    def app_clear_world(self):
        self.file_manager.clear_world(); self.current_filepath = None

    def prompt_for_hpp_file(self):
        root = Tk(); root.withdraw()
        path = filedialog.askopenfilename(
            title="Select BlockTypes.hpp",
            filetypes=(("C++ Header", "*.hpp"), ("All files", "*.*"))
        )
        root.destroy(); return path

    def quit(self):
        if hasattr(self, 'voxel_shader') and self.voxel_shader:
            glDeleteProgram(self.voxel_shader)
        if hasattr(self, 'ui_manager'):
            self.ui_manager.shutdown() #
        if hasattr(self, 'scene'):
            self.scene.destroy() #
        if hasattr(self, 'window'):
            glfw.destroy_window(self.window)
        glfw.terminate()

if __name__ == "__main__":
    my_app = None
    try:
        my_app = App()
        my_app.run()
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if my_app:
            my_app.quit()