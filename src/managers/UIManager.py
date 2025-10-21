# -*- coding: utf-8 -*-

from imgui.integrations.glfw import GlfwRenderer
import os
import time
import imgui
import glfw

class UIManager:
    def __init__(self, window, app):
        self.renderer = GlfwRenderer(window)
        self.app = app
        # NOTE: We intentionally do NOT register a GLFW mouse-button callback
        # here because the application (VlxTool.App) also needs to handle
        # mouse buttons for camera panning/orbiting. The App installs its own
        # callback and will forward events to this manager via
        # `UIManager.on_mouse_button` so both systems cooperate.

    def on_mouse_button(self, win, button, action, mods):
        """Handle mouse button events forwarded from the App-level callback.
        This contains the in-game placement/removal logic and respects
        ImGui's capture flags and the app's `is_mouse_captured` state.
        """
        io = imgui.get_io() # type: ignore[attr-defined]
        # Si ImGui quiere el mouse o el app no tiene el mouse capturado, no hacemos nada.
        if io.want_capture_mouse or not self.app.is_mouse_captured:
            return

        if action == glfw.PRESS:
            # Left click -> place a voxel at place_voxel_pos (if available)
            if button == glfw.MOUSE_BUTTON_LEFT and self.app.place_voxel_pos:
                # Debug: log the click and target
                try:
                    print(f"UI: Left click - place_voxel_pos={self.app.place_voxel_pos}, active_block_type={self.app.active_block_type}")
                except Exception:
                    pass
                try:
                    # World expects an integer value for the block id (or an Enum)
                    self.app.scene.world.set_voxel(*self.app.place_voxel_pos, self.app.active_block_type)
                    try:
                        print(f"UI: Requested place at {self.app.place_voxel_pos}")
                    except Exception:
                        pass
                except Exception as e:
                    # Log exception so we can see what's going wrong
                    try:
                        print(f"UI: Exception while placing voxel: {e}")
                    except Exception:
                        pass
            # Right click -> remove (set to Air) at hit_voxel_pos (if available)
            elif button == glfw.MOUSE_BUTTON_RIGHT and self.app.hit_voxel_pos:
                try:
                    self.app.scene.world.set_voxel(*self.app.hit_voxel_pos, self.app.BlockType.Air)
                except Exception:
                    pass

    def format_time_ago(self, timestamp):
        if not timestamp: return ""
        diff = time.time() - timestamp
        if diff < 60: val = int(diff); return f"{val} second{'s' if val != 1 else ''} ago"
        if diff < 3600: val = int(diff / 60); return f"{val} minute{'s' if val != 1 else ''} ago"
        if diff < 86400: val = int(diff / 3600); return f"{val} hour{'s' if val != 1 else ''} ago"
        val = int(diff / 86400); return f"{val} day{'s' if val != 1 else ''} ago"

    def render_ui(self):
        imgui.new_frame() # type: ignore[attr-defined]
        # Crosshair removed: we always show the OS cursor. When the user is
        # actively rotating/panning the cursor will be hidden and centered by
        # the application; no overlay crosshair is necessary.
        self.draw_main_window()
        imgui.render() # type: ignore[attr-defined]
        self.renderer.render(imgui.get_draw_data()) # type: ignore[attr-defined]
        
    def draw_crosshair(self):
        draw_list = imgui.get_background_draw_list() # type: ignore[attr-defined]
        io = imgui.get_io() # type: ignore[attr-defined]
        center = (io.display_size.x / 2, io.display_size.y / 2)
        draw_list.add_circle_filled(center[0], center[1], 3.0, imgui.get_color_u32_rgba(1, 1, 1, 0.8)) # type: ignore[attr-defined]

    def draw_main_window(self):
        imgui.begin("VlxTool") # type: ignore[attr-defined]
        
        filename = os.path.basename(self.app.current_filepath) if self.app.current_filepath else "Untitled"
        imgui.text(f"Current File: {filename}"); imgui.separator() # type: ignore[attr-defined]

        # Show current raycast/highlight info
        face_name = self.app.face_name_from_normal()
        hit = tuple(map(int, self.app.hit_voxel_pos)) if self.app.hit_voxel_pos else "-"
        place = tuple(map(int, self.app.place_voxel_pos)) if self.app.place_voxel_pos else "-"
        imgui.text(f"Target Face: {face_name}") # type: ignore[attr-defined]
        imgui.text(f"Hit Voxel: {hit}") # type: ignore[attr-defined]
        imgui.text(f"Place Voxel: {place}") # type: ignore[attr-defined]
        imgui.separator() # type: ignore[attr-defined]
        
        block_names = [bt.name for bt in self.app.placeable_blocks]
        current_idx = self.app.placeable_blocks.index(self.app.active_block_type) if self.app.active_block_type in self.app.placeable_blocks else 0
        imgui.text("Selected Block:") # type: ignore[attr-defined]
        changed, new_idx = imgui.combo("##BlockSelector", current_idx, block_names) # type: ignore[attr-defined]
        if changed: self.app.active_block_type = self.app.placeable_blocks[new_idx] 
        
        imgui.separator() # type: ignore[attr-defined]
        if imgui.button("Save"): self.app.app_save_world() # type: ignore[attr-defined]
        imgui.same_line() # type: ignore[attr-defined]
        if imgui.button("Load"): self.app.app_load_world() # type: ignore[attr-defined]
        imgui.same_line() # type: ignore[attr-defined]
        if imgui.button("Clear"): self.app.app_clear_world() # type: ignore[attr-defined]
        
        imgui.separator(); imgui.text("Recent Files") # type: ignore[attr-defined]
        imgui.begin_child("HistoryRegion", height=150, border=True) # type: ignore[attr-defined]
        for i, entry in enumerate(list(self.app.history_manager.get_history())):
            filepath = entry.get('path', 'Unknown'); timestamp = entry.get('timestamp')
            time_ago = "(Current)" if filepath == self.app.current_filepath else f"({self.format_time_ago(timestamp)})"
            
            imgui.text_unformatted(os.path.basename(filepath)) # type: ignore[attr-defined]
            if imgui.is_item_hovered(): imgui.set_tooltip(filepath) # type: ignore[attr-defined]
            
            imgui.same_line(); imgui.push_style_color(imgui.COLOR_TEXT, 0.6, 0.6, 0.6, 1); imgui.text_unformatted(time_ago); imgui.pop_style_color() # type: ignore[attr-defined]
            
            imgui.same_line(imgui.get_window_width() - 130) # type: ignore[attr-defined]
            if imgui.button(f"Load##{i}"): self.app.app_load_from_history(filepath) # type: ignore[attr-defined]
            imgui.same_line() # type: ignore[attr-defined]
            if imgui.button(f"Remove##{i}"): self.app.history_manager.remove_entry(filepath) # type: ignore[attr-defined]
        imgui.end_child() # type: ignore[attr-defined]
        imgui.end() # type: ignore[attr-defined]

    def shutdown(self):
        self.renderer.shutdown()