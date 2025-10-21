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
            # If ImGui doesn't have the mouse and the app has it captured
            if button == glfw.MOUSE_BUTTON_LEFT and self.app.place_voxel_pos:
                # If waiting for pivot, that takes precedence
                if getattr(self.app, 'waiting_for_pivot', False):
                    try:
                        px, py, pz = tuple(map(int, self.app.place_voxel_pos))
                        self.app.scene.world.pivot = (px, py, pz)
                        self.app.waiting_for_pivot = False
                        try: print(f"Pivot set to {(px,py,pz)}")
                        except Exception: pass
                        return
                    except Exception:
                        self.app.waiting_for_pivot = False

                # Mode-based behavior
                mode = getattr(self.app, 'edit_mode', 'place')
                try:
                    if mode == 'place':
                        x, y, z = tuple(map(int, self.app.place_voxel_pos))
                        prev = self.app.scene.world.get_voxel(x, y, z)
                        new = int(getattr(self.app.active_block_type, 'value', self.app.active_block_type))
                        self.app.action_history.record({'type':'set', 'pos':(x, y, z), 'prev':prev, 'new':new})
                        self.app.scene.world.set_voxel(x, y, z, new)
                    elif mode == 'erase':
                        x, y, z = tuple(map(int, self.app.place_voxel_pos))
                        prev = self.app.scene.world.get_voxel(x, y, z)
                        new = 0
                        self.app.action_history.record({'type':'set', 'pos':(x, y, z), 'prev':prev, 'new':new})
                        self.app.scene.world.set_voxel(x, y, z, new)
                    elif mode == 'paint':
                        if self.app.hit_voxel_pos and self.app.scene.world.is_solid(*self.app.hit_voxel_pos):
                            x, y, z = tuple(map(int, self.app.hit_voxel_pos))
                            prev = self.app.scene.world.get_voxel(x, y, z)
                            new = int(getattr(self.app.active_block_type, 'value', self.app.active_block_type))
                            self.app.action_history.record({'type':'set', 'pos':(x, y, z), 'prev':prev, 'new':new})
                            self.app.scene.world.set_voxel(x, y, z, new)
                    # Debug logging
                    try: print(f"UI: {mode} action at {self.app.place_voxel_pos}")
                    except Exception: pass
                except Exception as e:
                    try: print(f"UI: Exception during {mode}: {e}")
                    except Exception: pass
            # Right click -> removal disabled (no-op)
            elif button == glfw.MOUSE_BUTTON_RIGHT and self.app.hit_voxel_pos:
                # Removal via right-click has been intentionally disabled.
                # Keep this branch as a no-op so the UI still consumes the
                # event if necessary but does not mutate the world.
                try:
                    # Optional debug logging can be enabled here.
                    # print("UI: Right click - removal ignored")
                    pass
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
        self.draw_left_panel()
        self.draw_right_panel()
        imgui.render() # type: ignore[attr-defined]
        self.renderer.render(imgui.get_draw_data()) # type: ignore[attr-defined]
        
    def draw_crosshair(self):
        draw_list = imgui.get_background_draw_list() # type: ignore[attr-defined]
        io = imgui.get_io() # type: ignore[attr-defined]
        center = (io.display_size.x / 2, io.display_size.y / 2)
        draw_list.add_circle_filled(center[0], center[1], 3.0, imgui.get_color_u32_rgba(1, 1, 1, 0.8)) # type: ignore[attr-defined]

    def draw_left_panel(self):
        # Parent window - will contain two child panels side by side
        imgui.begin("VlxTool")

        io = imgui.get_io()
        total_w = io.display_size.x
        total_h = io.display_size.y

        left_w = 300
        right_w = 360
        center_w = max(0, total_w - left_w - right_w)

        # Left child panel
        imgui.begin_child("LeftPanel", width=left_w, height=total_h - 120, border=False)
        imgui.text("Blocks")
        imgui.separator()

        # Grid of block buttons (show color on hover and tooltip with name)
        cols = 4
        sw = 48
        sh = 48
        for idx, bt in enumerate(self.app.placeable_blocks):
            try:
                # BLOCK_COLORS keys are enum members (or ints). Use the exact key.
                color = self.app.BLOCK_COLORS.get(bt, None)
                if color is None:
                    # try fallback by numeric value
                    try:
                        color = self.app.BLOCK_COLORS.get(int(bt), None)
                    except Exception:
                        color = None
                if color is None:
                    color = (0.6, 0.6, 0.6)
                # ensure RGB triple of floats in 0..1
                r, g, b = float(color[0]), float(color[1]), float(color[2])
                color = (r, g, b)
            except Exception:
                color = (0.6, 0.6, 0.6)

            imgui.push_style_color(imgui.COLOR_BUTTON, color[0], color[1], color[2], 1.0)
            if imgui.button(f"##blk{idx}", sw, sh):
                self.app.active_block_type = bt
            imgui.pop_style_color()

            if imgui.is_item_hovered():
                imgui.set_tooltip(bt.name)

            if (idx % cols) != (cols - 1):
                imgui.same_line()

        imgui.separator()
        imgui.text(f"Selected: {self.app.active_block_type.name if self.app.active_block_type else 'None'}")
        imgui.separator()

        # Action buttons
        if imgui.button("Place"):
            self.app.edit_mode = 'place'
        imgui.same_line()
        if imgui.button("Erase"):
            self.app.edit_mode = 'erase'
        imgui.same_line()
        if imgui.button("Paint"):
            self.app.edit_mode = 'paint'
        imgui.separator()
        if imgui.button("Undo"):
            try: self.app.action_history.undo(self.app.scene.world)
            except Exception: pass
        imgui.same_line()
        if imgui.button("Redo"):
            try: self.app.action_history.redo(self.app.scene.world)
            except Exception: pass
        imgui.separator()
        if imgui.button("Clear"):
            self.app.app_clear_world()
        imgui.end_child()
        imgui.end()

    def draw_right_panel(self):
        # Separate ImGui window for file/save/history
        imgui.begin("File & History")
        filename = os.path.basename(self.app.current_filepath) if self.app.current_filepath else "Untitled"
        imgui.text(f"Current File: {filename}")
        imgui.separator()

        if imgui.button("Save"): self.app.app_save_world()
        imgui.same_line()
        if imgui.button("Load"): self.app.app_load_world()

        imgui.separator(); imgui.text("Recent Files")
        total_h = imgui.get_io().display_size.y
        imgui.begin_child("HistoryRegion", height=total_h - 120, border=True)
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