# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_submodules

# --- Имена и пути ---
APP_NAME = "TorrServer"                    
BUNDLE_ID = "com.torrserver.macedition"     
APP_VERSION = "1.0"
SCRIPT = "TorrServerMacEdition.py"          
APP_ICON = "icon.icns"

# --- Ресурсы (иконки для rumps) ---
datas = [
    ('on.png', '.'),
    ('off.png', '.'),
    ('think.png', '.'),
    ('update.png', '.'),
    ('logo.png', '.'),
]

# --- rumps ---
hiddenimports = collect_submodules('rumps') + [
    'objc',
    'AppKit',
    'Foundation',
    'Cocoa',
    'Quartz',
    'Security',
]

a = Analysis(
    [SCRIPT],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,               
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch='x86_64',        # darwin-amd64
    codesign_identity=None,
    entitlements_file=None,
)

app = BUNDLE(
    exe,
    a.binaries,
    a.datas,
    name=f'{APP_NAME}.app',
    icon=APP_ICON,
    bundle_identifier=BUNDLE_ID,
    info_plist={
        'CFBundleName': 'TorrServer',
        'CFBundleDisplayName': 'TorrServer',
        'CFBundleShortVersionString': APP_VERSION,
        'CFBundleVersion': APP_VERSION,
        'LSUIElement': True,
        'NSHumanReadableCopyright': 'Copyright © 2026 unknalex. GPL-3.0-or-later.',
    },
)
