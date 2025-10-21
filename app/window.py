import os
import sys
import glfw
from src.utils.Config import SCREEN_WIDTH, SCREEN_HEIGHT, create_shader_program
from OpenGL.GL import (
    glClearColor,
    glEnable,
    glCullFace,
    glFrontFace,
    glDeleteProgram,
    GL_DEPTH_TEST,
    GL_CULL_FACE,
    GL_BACK,
    GL_CW,
)


def initialize_glfw(app):
    if not glfw.init():
        sys.exit("Could not initialize GLFW")
    # prefer modern OpenGL 3.3 core
    from glfw.GLFW import GLFW_CONTEXT_VERSION_MAJOR, GLFW_CONTEXT_VERSION_MINOR, GLFW_OPENGL_PROFILE, GLFW_OPENGL_CORE_PROFILE, GLFW_OPENGL_FORWARD_COMPAT, GLFW_TRUE, GLFW_CURSOR, GLFW_CURSOR_NORMAL
    glfw.window_hint(GLFW_CONTEXT_VERSION_MAJOR, 3)
    glfw.window_hint(GLFW_CONTEXT_VERSION_MINOR, 3)
    glfw.window_hint(GLFW_OPENGL_PROFILE, GLFW_OPENGL_CORE_PROFILE)
    glfw.window_hint(GLFW_OPENGL_FORWARD_COMPAT, GLFW_TRUE)
    app.window = glfw.create_window(SCREEN_WIDTH, SCREEN_HEIGHT, "VlxTool", None, None)
    if not app.window:
        glfw.terminate()
        sys.exit("Could not create window")
    glfw.make_context_current(app.window)
    glfw.set_input_mode(app.window, GLFW_CURSOR, GLFW_CURSOR_NORMAL)


def initialize_opengl(app):
    # Basic GL state
    glClearColor(0.15, 0.15, 0.15, 1)
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_CULL_FACE)
    glCullFace(GL_BACK)
    glFrontFace(GL_CW)

    # Shader files are in the repository top-level `shaders/` directory
    vert = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "shaders", "voxel.vert")
    frag = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "shaders", "voxel.frag")
    vert = os.path.normpath(vert)
    frag = os.path.normpath(frag)
    app.voxel_shader = create_shader_program(vert, frag)
    if not getattr(app, 'voxel_shader', None):
        sys.exit("Voxel shader failed to compile.")


def destroy_shader(app):
    if hasattr(app, 'voxel_shader') and app.voxel_shader:
        try:
            glDeleteProgram(app.voxel_shader)
        except Exception:
            pass
