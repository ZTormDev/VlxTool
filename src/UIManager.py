# src/UIManager.py
import os
import time
import imgui
from imgui.integrations.glfw import GlfwRenderer
import glfw

class UIManager:
    def __init__(self, window, app):
        self.renderer = GlfwRenderer(window)
        self.app = app
        
        def mouse_button_callback(win, button, action, mods):
            io = imgui.get_io()
            # Esta condición es la clave: si ImGui quiere el mouse, no hacemos nada en el juego.
            # Y si el mouse no está capturado (p.ej. al presionar ALT), tampoco.
            if io.want_capture_mouse or not self.app.is_mouse_captured:
                return

            if action == glfw.PRESS:
                if button == glfw.MOUSE_BUTTON_LEFT and self.app.hit_voxel_pos:
                    self.app.scene.world.set_voxel(*self.app.hit_voxel_pos, self.app.BlockType.Air)
                elif button == glfw.MOUSE_BUTTON_RIGHT and self.app.place_voxel_pos:
                    self.app.scene.world.set_voxel(*self.app.place_voxel_pos, self.app.active_block_type)
        
        # Le pasamos el callback anidado a GLFW.
        # El callback del renderer de ImGui se llama por separado en VlxTool.py
        glfw.set_mouse_button_callback(window, mouse_button_callback)

    def format_time_ago(self, timestamp):
        if not timestamp: return ""
        diff = time.time() - timestamp
        if diff < 60: val = int(diff); return f"{val} second{'s' if val != 1 else ''} ago"
        if diff < 3600: val = int(diff / 60); return f"{val} minute{'s' if val != 1 else ''} ago"
        if diff < 86400: val = int(diff / 3600); return f"{val} hour{'s' if val != 1 else ''} ago"
        val = int(diff / 86400); return f"{val} day{'s' if val != 1 else ''} ago"

    def render_ui(self):
        imgui.new_frame()
        if self.app.is_mouse_captured: self.draw_crosshair()
        self.draw_main_window()
        imgui.render()
        self.renderer.render(imgui.get_draw_data())
        
    def draw_crosshair(self):
        draw_list = imgui.get_background_draw_list()
        io = imgui.get_io()
        center = (io.display_size.x / 2, io.display_size.y / 2)
        draw_list.add_circle_filled(center[0], center[1], 3.0, imgui.get_color_u32_rgba(1, 1, 1, 0.8))

    def draw_main_window(self):
        imgui.begin("VlxTool")
        
        filename = os.path.basename(self.app.current_filepath) if self.app.current_filepath else "Untitled"
        imgui.text(f"Current File: {filename}"); imgui.separator()

        # Show current raycast/highlight info
        face_name = self.app.face_name_from_normal()
        hit = tuple(map(int, self.app.hit_voxel_pos)) if self.app.hit_voxel_pos else "-"
        place = tuple(map(int, self.app.place_voxel_pos)) if self.app.place_voxel_pos else "-"
        imgui.text(f"Target Face: {face_name}")
        imgui.text(f"Hit Voxel: {hit}")
        imgui.text(f"Place Voxel: {place}")
        imgui.separator()
        
        block_names = [bt.name for bt in self.app.placeable_blocks]
        current_idx = self.app.placeable_blocks.index(self.app.active_block_type) if self.app.active_block_type in self.app.placeable_blocks else 0
        imgui.text("Selected Block:")
        changed, new_idx = imgui.combo("##BlockSelector", current_idx, block_names)
        if changed: self.app.active_block_type = self.app.placeable_blocks[new_idx]
        
        imgui.separator()
        if imgui.button("Save"): self.app.app_save_world()
        imgui.same_line()
        if imgui.button("Load"): self.app.app_load_world()
        imgui.same_line()
        if imgui.button("Clear"): self.app.app_clear_world()
        
        imgui.separator(); imgui.text("Recent Files")
        imgui.begin_child("HistoryRegion", height=150, border=True)
        for i, entry in enumerate(list(self.app.history_manager.get_history())):
            filepath = entry.get('path', 'Unknown'); timestamp = entry.get('timestamp')
            time_ago = "(Current)" if filepath == self.app.current_filepath else f"({self.format_time_ago(timestamp)})"
            
            imgui.text_unformatted(os.path.basename(filepath))
            if imgui.is_item_hovered(): imgui.set_tooltip(filepath)
            
            imgui.same_line(); imgui.push_style_color(imgui.COLOR_TEXT, 0.6, 0.6, 0.6, 1); imgui.text_unformatted(time_ago); imgui.pop_style_color()
            
            imgui.same_line(imgui.get_window_width() - 130)
            if imgui.button(f"Load##{i}"): self.app.app_load_from_history(filepath)
            imgui.same_line()
            if imgui.button(f"Remove##{i}"): self.app.history_manager.remove_entry(filepath)
        imgui.end_child()
        imgui.end()

    def shutdown(self):
        self.renderer.shutdown()