# VlxTool.py
import os
import sys
import numpy as np
import pyrr
import glfw
import imgui
from OpenGL.GL import *
from tkinter import Tk, filedialog

# Importaciones de los módulos del proyecto
from src.Camera import Camera
from src.Scene import Scene
from src.Config import SCREEN_WIDTH, SCREEN_HEIGHT, create_shader_program
from src.BlockTypes import load_from_hpp
from src.Raycast import Raycast
from src.SettingsManager import SettingsManager
from src.HistoryManager import HistoryManager
from src.FileManager import FileManager
from src.UIManager import UIManager

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
        self.settings_manager = SettingsManager() #
        self.history_manager = HistoryManager(self.settings_manager.settings_dir) #
        
        settings = self.settings_manager.load_settings() #
        hpp_path = settings.get('hpp_path') if settings else None
        if not hpp_path:
            hpp_path = self.prompt_for_hpp_file()
            if hpp_path: self.settings_manager.save_settings({'hpp_path': hpp_path}) #
        if not hpp_path: sys.exit("No .hpp file selected.")

        # --- Inicialización de Componentes Gráficos y del Mundo ---
        self.initialize_glfw()
        self.BlockType, self.BLOCK_COLORS = load_from_hpp(hpp_path) #
        imgui.create_context()
        
        # La clase Scene ahora se encarga de crear el mundo, la rejilla, etc.
        self.scene = Scene(self.BlockType, self.BLOCK_COLORS) #
        
        self.camera = self.initialize_camera()
        
        # --- Inicialización de Gestores Dependientes ---
        self.file_manager = FileManager(self.scene.world, self.BlockType, self.history_manager) #
        self.ui_manager = UIManager(self.window, self) #

        # --- Estado de la Aplicación ---
        self.is_mouse_captured = True
        self.alt_pressed_last_frame = False
        self.hit_voxel_pos, self.place_voxel_pos, self.hit_voxel_normal = None, None, None
        self.current_filepath = None
        self.placeable_blocks = [bt for bt in self.BlockType if bt != self.BlockType.Air]
        self.active_block_type = self.placeable_blocks[0] if self.placeable_blocks else None

        self.initialize_opengl()
        self.set_callbacks()

    def initialize_glfw(self):
        if not glfw.init(): sys.exit("Could not initialize GLFW")
        glfw.window_hint(GLFW_CONTEXT_VERSION_MAJOR, 3); glfw.window_hint(GLFW_CONTEXT_VERSION_MINOR, 3)
        glfw.window_hint(GLFW_OPENGL_PROFILE, GLFW_OPENGL_CORE_PROFILE); glfw.window_hint(GLFW_OPENGL_FORWARD_COMPAT, GLFW_TRUE)
        self.window = glfw.create_window(SCREEN_WIDTH, SCREEN_HEIGHT, "VlxTool", None, None)
        if not self.window: glfw.terminate(); sys.exit("Could not create window")
        glfw.make_context_current(self.window); glfw.set_input_mode(self.window, GLFW_CURSOR, GLFW_CURSOR_DISABLED)

    def initialize_camera(self):
        world_coord_size = self.scene.world.chunk_size * self.scene.world.world_size_in_chunks #
        return Camera(
            position=[world_coord_size / 2, world_coord_size / 2 + 10, world_coord_size / 2],
            target=[0, 0, 0]
        ) #

    def set_callbacks(self):
        glfw.set_cursor_pos_callback(self.window, self.mouse_look_callback)
        glfw.set_scroll_callback(self.window, self.scroll_callback)
        
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
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        view = self.camera.get_view_matrix() #
        proj = pyrr.matrix44.create_perspective_projection(75, SCREEN_WIDTH/SCREEN_HEIGHT, 0.1, 512, np.float32)
        
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
        
        sprint = glfw.get_key(self.window, GLFW_KEY_LEFT_SHIFT) == GLFW_PRESS
        key_map = {
            GLFW_KEY_W: "FORWARD", GLFW_KEY_S: "BACKWARD", 
            GLFW_KEY_A: "LEFT", GLFW_KEY_D: "RIGHT",
            GLFW_KEY_SPACE: "UP", GLFW_KEY_LEFT_CONTROL: "DOWN"
        }
        for key, direction in key_map.items():
            if glfw.get_key(self.window, key) == GLFW_PRESS:
                self.camera.process_keyboard(direction, delta_time, sprint) #

    def mouse_look_callback(self, window, xpos, ypos):
        if not self.is_mouse_captured: return
        w, h = glfw.get_window_size(window)
        center_x, center_y = w / 2, h / 2
        self.camera.process_mouse_movement(xpos - center_x, center_y - ypos) #
        glfw.set_cursor_pos(window, center_x, center_y)

    def scroll_callback(self, window, x_offset, y_offset):
        if not self.is_mouse_captured or not self.placeable_blocks: return
        try:
            idx = self.placeable_blocks.index(self.active_block_type)
            self.active_block_type = self.placeable_blocks[(idx - int(y_offset)) % len(self.placeable_blocks)]
        except ValueError:
            self.active_block_type = self.placeable_blocks[0]

    def update_raycast(self):
        if not self.is_mouse_captured:
            self.hit_voxel_pos = None
            return
            
        ray = Raycast(self.scene.world, self.camera.position, self.camera.front) #
        hit, place = ray.step_forward() #

        if hit:
            self.hit_voxel_pos, self.place_voxel_pos = hit, place
            self.hit_voxel_normal = tuple(np.subtract(place, hit))
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
        if path := self.file_manager.save_world(): self.current_filepath = path #
    def app_load_world(self):
        if path := self.file_manager.load_world(): self.current_filepath = path #
    def app_load_from_history(self, path):
        if loaded_path := self.file_manager.load_world_from_path(path): self.current_filepath = loaded_path #
    def app_clear_world(self):
        self.file_manager.clear_world(); self.current_filepath = None #

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