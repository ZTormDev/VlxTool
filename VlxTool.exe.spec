# -*- mode: python ; coding: utf-8 -*-


import os

# Include GLFW DLLs from the virtualenv site-packages so the runtime can load them
venv_site = os.path.join(r"D:\ZETA\Desktop\VlxTool\.venv", 'Lib', 'site-packages', 'glfw')
glfw_dll = os.path.join(venv_site, 'glfw3.dll')
msvcr_dll = os.path.join(venv_site, 'msvcr120.dll')

a = Analysis(
    ['VlxTool.py'],
    pathex=[],
    binaries=[(glfw_dll, '.'), (msvcr_dll, '.')],
    datas=[('shaders', 'shaders'), ('app', 'app'), ('src', 'src')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='VlxTool.exe',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
