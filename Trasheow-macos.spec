# -*- mode: python ; coding: utf-8 -*-
#
# macOS build spec for Trasheow. Building via this spec (instead of a plain
# `pyinstaller ...` one-liner) is required so the generated .app bundle gets
# a custom Info.plist containing NSCameraUsageDescription - without it,
# macOS's TCC privacy system aborts the app the instant it opens the camera
# (SIGABRT, "attempted to access privacy-sensitive data without a usage
# description"), which is not a code or packaging bug, just a missing
# permission-prompt string that PyInstaller does not add by default.
#
# Build with:
#   pyinstaller Trasheow-macos.spec

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('gui/purple_theme.json', 'gui'), ('assets', 'assets')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PyQt5', 'PyQt6', 'PySide2', 'PySide6'],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Trasheow',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon='assets/trasheow_logo.icns',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Trasheow',
)

app = BUNDLE(
    coll,
    name='Trasheow.app',
    icon='assets/trasheow_logo.icns',
    bundle_identifier='com.trasheow.app',
    info_plist={
        'NSCameraUsageDescription': 'Trasheow uses the camera to capture photos of waste so it can classify them with AI.',
        'NSHighResolutionCapable': True,
        'CFBundleShortVersionString': '1.0.0',
    },
)
