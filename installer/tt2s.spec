# -*- mode: python ; coding: utf-8 -*-
# Spec lives in installer/ — use SPECPATH to reach the project root one level up.

import os
ROOT = os.path.abspath(os.path.join(SPECPATH, '..'))

# ── Main application ─────────────────────────────────────────────────────────
a_main = Analysis(
    [os.path.join(ROOT, 'tt2s.py')],
    pathex=[ROOT],
    binaries=[],
    datas=[(os.path.join(ROOT, 'assets', 'icon.ico'), '.')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz_main = PYZ(a_main.pure)

exe_main = EXE(
    pyz_main,
    a_main.scripts,
    a_main.binaries,
    a_main.datas,
    [],
    name='tt2s',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    icon=os.path.join(ROOT, 'assets', 'icon.ico'),
)

# ── Notification popup (subprocess) ──────────────────────────────────────────
a_popup = Analysis(
    [os.path.join(ROOT, 'src', 'notif_popup.py')],
    pathex=[ROOT],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz_popup = PYZ(a_popup.pure)

exe_popup = EXE(
    pyz_popup,
    a_popup.scripts,
    a_popup.binaries,
    a_popup.datas,
    [],
    name='notif_popup',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    icon=os.path.join(ROOT, 'assets', 'icon.ico'),
)
