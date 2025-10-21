"""Application class extracted from top-level `VlxTool.py`.

This module contains the App class and its logic. It's intended to be
imported from the top-level launcher which keeps a minimal entrypoint.
"""
import os
import sys
import numpy as np
import pyrr
import glfw
import imgui  # type: ignore
import math
from typing import cast, Tuple

from OpenGL.GL import glClear, glDeleteProgram, GL_COLOR_BUFFER_BIT, GL_DEPTH_BUFFER_BIT
from tkinter import Tk, filedialog

# Importaciones de los módulos del proyecto
from src.core.Camera import Camera
from src.core.Scene import Scene
from src.utils.Config import SCREEN_WIDTH, SCREEN_HEIGHT
from src.utils.BlockTypes import load_from_hpp
from src.managers.SettingsManager import SettingsManager
from src.managers.HistoryManager import HistoryManager
from src.managers.FileManager import FileManager
from src.managers.UIManager import UIManager
from src.managers.ActionHistory import ActionHistory

# modular responsibilities
from app import window as window_mod
from app import camera_ctrl as camera_mod
from app import raycast as raycast_mod
from app import io as io_mod
from app import ui as ui_mod

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
        # Initialize GLFW and window
        window_mod.initialize_glfw(self)

        # Load block types and create ImGui context
        self.BlockType, self.BLOCK_COLORS = load_from_hpp(hpp_path)
        imgui.create_context()  # type: ignore[attr-defined]

        # The Scene builds world, grid, etc.
        self.scene = Scene(self.BlockType, self.BLOCK_COLORS)

        self.camera = self.initialize_camera()

        # dependent managers
        self.file_manager = FileManager(self.scene.world, self.BlockType, self.history_manager)
        # Action history for undo/redo of voxel operations
        self.action_history = ActionHistory()
        # UI manager will be created via ui_mod to allow later swapping/testing
        ui_mod.init_ui(self)

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
        # Pivot set mode: when True, the next left click will set world.pivot
        self.waiting_for_pivot = False

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

        # Initialize GL state and set callbacks
        window_mod.initialize_opengl(self)
        camera_mod.set_callbacks(self)

    def initialize_glfw(self):
        # kept for backward compatibility; new code uses window_mod
        window_mod.initialize_glfw(self)

    def initialize_camera(self):
        # The World now exposes `total_size` which is the voxel size per axis
        world_coord_size = getattr(self.scene.world, 'total_size',
                                   self.scene.world.base_chunk_size * self.scene.world.world_size_in_chunks)
        return Camera(
            position=[world_coord_size / 2, world_coord_size / 2, world_coord_size / 2],
            # default target at world center
            target=[world_coord_size / 2, 5, world_coord_size / 2]
        ) #

    def set_callbacks(self):
        camera_mod.set_callbacks(self)
        
    def initialize_opengl(self):
        window_mod.initialize_opengl(self)

    def run(self):
        last_time = glfw.get_time()
        while not glfw.window_should_close(self.window):
            current_time = glfw.get_time()
            delta_time = current_time - last_time
            last_time = current_time
            
            glfw.poll_events()
            # UI renderer input processing
            if hasattr(self, 'ui_manager') and getattr(self.ui_manager, 'renderer', None):
                self.ui_manager.renderer.process_inputs()
            self.process_input(delta_time)
            # perform raycast update via module
            raycast_mod.update_raycast(self)
            self.scene.world.update_dirty_chunks() #
            
            self.render_frame()
            
            glfw.swap_buffers(self.window)

    def render_frame(self):
        mask = GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT  # type: ignore[arg-type]
        glClear(mask)
        view = self.camera.get_view_matrix() #
        proj = pyrr.matrix44.create_perspective_projection(75, SCREEN_WIDTH/SCREEN_HEIGHT, 0.1, 1024, np.float32)

        # La clase Scene se encarga de toda la lógica de renderizado
        self.scene.render(proj, view, self.voxel_shader, self.hit_voxel_pos, self.hit_voxel_normal)
        if hasattr(self, 'ui_manager'):
            self.ui_manager.render_ui()

    def process_input(self, delta_time):
        if glfw.get_key(self.window, GLFW_KEY_ESCAPE) == GLFW_PRESS:
            glfw.set_window_should_close(self.window, True)

        # Toggle pivot-set mode with the 'P' key
        try:
            if glfw.get_key(self.window, glfw.KEY_P) == GLFW_PRESS:
                # Enter pivot set mode; UIManager will use place_voxel_pos on next left click
                self.waiting_for_pivot = True
        except Exception:
            pass
        

    def mouse_look_callback(self, window, xpos, ypos):
        camera_mod.handle_mouse_look(self, window, xpos, ypos)

    def scroll_callback(self, window, x_offset, y_offset):
        # Use mouse wheel to zoom camera distance (always)
        camera_mod.handle_scroll(self, window, x_offset, y_offset)

    def mouse_button_callback(self, window, button, action, mods):
        camera_mod.handle_mouse_button(self, window, button, action, mods)

    def update_raycast(self):
        raycast_mod.update_raycast(self)

    def face_name_from_normal(self):
        """Return a human-friendly face name derived from current hit normal."""
        return raycast_mod.face_name_from_normal(self.hit_voxel_normal)

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
        return io_mod.prompt_for_hpp_file()

    def quit(self):
        window_mod.destroy_shader(self)
        if hasattr(self, 'ui_manager'):
            try:
                self.ui_manager.shutdown()
            except Exception:
                pass
        if hasattr(self, 'scene'):
            try:
                self.scene.destroy()
            except Exception:
                pass
        if hasattr(self, 'window'):
            try:
                glfw.destroy_window(self.window)
            except Exception:
                pass
        glfw.terminate()


__all__ = ["App"]
