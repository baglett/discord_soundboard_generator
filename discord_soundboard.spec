# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Discord Soundboard Generator
This creates a distributable executable with all necessary dependencies
"""

import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Collect all hidden imports for dependencies
hidden_imports = [
    'pygame',
    'pydub',
    'yt_dlp',
    'requests',
    'dotenv',
    'audioop_lts',
    'tkinter',
    'tkinter.ttk',
    'tkinter.font',
    'tkinter.messagebox',
    'tkinter.filedialog',
    'threading',
    'json',
    'base64',
    'pathlib',
    # pkg_resources dependencies
    'pkg_resources',
    'pkg_resources._vendor',
    'pkg_resources.extern',
    'jaraco',
    'jaraco.text',
    'jaraco.functools',
    'jaraco.context',
    'more_itertools',
    'platformdirs',
]

# Collect all data files from yt-dlp
datas = collect_data_files('yt_dlp')

# Add setup directory
datas += [('setup', 'setup')]

# Add an empty sounds directory structure
datas += [('sounds', 'sounds')]

# Bundle FFmpeg binaries if they exist
import os
if os.path.exists('ffmpeg'):
    if os.path.exists('ffmpeg/ffmpeg.exe'):
        datas += [('ffmpeg/ffmpeg.exe', 'ffmpeg')]
    if os.path.exists('ffmpeg/ffprobe.exe'):
        datas += [('ffmpeg/ffprobe.exe', 'ffmpeg')]
    print("INFO: FFmpeg binaries will be bundled with the executable")

# Main analysis - collects all imports and dependencies
a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['hook-pkg_resources.py'],
    excludes=[
        'matplotlib',
        'numpy',
        'pandas',
        'PIL',
        'scipy',
        'setuptools',
        'wheel',
        'pip',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Process collected files
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Create the executable
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='DiscordSoundboardGenerator',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Windowed application (no console window)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add icon path here if you have one: 'icon.ico'
)

# Collect all files into a directory
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='DiscordSoundboardGenerator',
)
