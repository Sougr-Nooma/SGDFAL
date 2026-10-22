# -*- mode: python ; coding: utf-8 -*-
import os
from pathlib import Path

project_directory = Path(SPECPATH)
icon_path = Path(os.environ["SGD_MACOS_ICON"])

a = Analysis(
    [str(project_directory / "main.py")],
    pathex=[str(project_directory)],
    binaries=[],
    datas=[
        (str(project_directory / "SGD.png"), "."),
        (str(project_directory / "SGD.ico"), "."),
    ],
    hiddenimports=["tkcalendar", "matplotlib.backends.backend_tkagg"],
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
    name="GestionRestaurant",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

app = BUNDLE(
    exe,
    name="SGD.app",
    icon=str(icon_path),
    bundle_identifier="com.sgd.gestionrestaurant",
    info_plist={
        "CFBundleName": "SGD",
        "CFBundleDisplayName": "SGD - Gestion Restaurant",
        "LSMinimumSystemVersion": "10.13",
        "NSHighResolutionCapable": "True",
    },
)
