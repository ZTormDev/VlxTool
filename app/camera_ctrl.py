import math
import glfw
import numpy as np


def set_callbacks(app):
    glfw.set_cursor_pos_callback(app.window, app.mouse_look_callback)
    glfw.set_scroll_callback(app.window, app.scroll_callback)
    glfw.set_mouse_button_callback(app.window, app.mouse_button_callback)


# Camera helper functions that operate on the app.camera instance
def handle_mouse_look(app, window, xpos, ypos):
    if getattr(app, 'just_centered', False):
        app.just_centered = False
        app.last_cursor_pos = (xpos, ypos)
        return
    if app.is_mouse_captured:
        w, h = glfw.get_window_size(window)
        center_x, center_y = w / 2, h / 2
        if app.middle_button_down:
            dx = xpos - center_x
            dy = ypos - center_y
            app.camera.pan(dx, dy)
            glfw.set_cursor_pos(window, center_x, center_y)
            return
        if app.right_button_down:
            dx = xpos - center_x
            dy = ypos - center_y
            app.camera.orbit(dx, dy)
            glfw.set_cursor_pos(window, center_x, center_y)
            return
        return

    if app.last_cursor_pos is None:
        app.last_cursor_pos = (xpos, ypos)
        return
    lx, ly = app.last_cursor_pos
    dx, dy = xpos - lx, ypos - ly
    app.last_cursor_pos = (xpos, ypos)
    if app.middle_button_down:
        app.camera.pan(dx, dy)
    elif app.right_button_down:
        app.camera.orbit(dx, dy)


def handle_scroll(app, window, x_offset, y_offset):
    app.camera.zoom(y_offset)


def handle_mouse_button(app, window, button, action, mods):
    # Forward to UI first
    try:
        if hasattr(app, 'ui_manager') and app.ui_manager:
            app.ui_manager.on_mouse_button(window, button, action, mods)
    except Exception:
        pass
    if button == glfw.MOUSE_BUTTON_MIDDLE:
        if action == glfw.PRESS:
            app.middle_button_down = True
            w, h = glfw.get_window_size(app.window)
            center_x, center_y = w / 2, h / 2
            glfw.set_cursor_pos(app.window, center_x, center_y)
            app.just_centered = True
            from glfw.GLFW import GLFW_CURSOR, GLFW_CURSOR_DISABLED
            glfw.set_input_mode(app.window, GLFW_CURSOR, GLFW_CURSOR_DISABLED)
            app.last_cursor_pos = (center_x, center_y)
        elif action == glfw.RELEASE:
            app.middle_button_down = False
            from glfw.GLFW import GLFW_CURSOR, GLFW_CURSOR_NORMAL
            glfw.set_input_mode(app.window, GLFW_CURSOR, GLFW_CURSOR_NORMAL)
    elif button == glfw.MOUSE_BUTTON_RIGHT:
        if action == glfw.PRESS:
            app.right_button_down = True
            w, h = glfw.get_window_size(app.window)
            center_x, center_y = w / 2, h / 2
            glfw.set_cursor_pos(app.window, center_x, center_y)
            app.just_centered = True
            from glfw.GLFW import GLFW_CURSOR, GLFW_CURSOR_DISABLED
            glfw.set_input_mode(app.window, GLFW_CURSOR, GLFW_CURSOR_DISABLED)
            app.last_cursor_pos = (center_x, center_y)
        elif action == glfw.RELEASE:
            app.right_button_down = False
            from glfw.GLFW import GLFW_CURSOR, GLFW_CURSOR_NORMAL
            glfw.set_input_mode(app.window, GLFW_CURSOR, GLFW_CURSOR_NORMAL)
