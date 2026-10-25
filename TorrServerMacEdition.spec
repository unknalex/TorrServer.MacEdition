# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['TorrServerMacEdition.py'],
    pathex=[],
    binaries=[],
    datas=[],
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
    [],
    exclude_binaries=True,
    name='TorrServer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['icon.icns'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='TorrServer',
)
app = BUNDLE(
    exe,
    name='TorrServer.app',
    icon='icon.icns',
    bundle_identifier='com.torrserver.macedition',
    info_plist={
        'NSHumanReadableCopyright': 'Copyright © 2026 unknalex. All rights reserved.',
        'CFBundleShortVersionString': '1.0',
        'CFBundleVersion': '1.0'
    },
)
