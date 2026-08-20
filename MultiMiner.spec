# -*- mode: python ; coding: utf-8 -*-
#
# Spec PyInstaller pour MultiMiner.
# Génère un exécutable "one-file" : MultiMiner.exe autonome.
#
# Note : le mode one-file extrait ses fichiers dans un dossier temporaire
# à chaque lancement (démarrage légèrement plus lent, quelques secondes).
# Si vous préférez un démarrage plus rapide, remplacez le bloc EXE/COLLECT
# ci-dessous par un mode "one-folder" (voir commentaire en bas du fichier).

import os

block_cipher = None

project_root = os.path.abspath(".")
icon_path = os.path.join(project_root, "assets", "icon.ico")
has_icon = os.path.isfile(icon_path)

a = Analysis(
    ["src/main.py"],
    pathex=[os.path.join(project_root, "src")],
    binaries=[],
    datas=[
        ("config/config.json", "config"),
        ("miner/README.txt", "miner"),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="MultiMiner",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_path if has_icon else None,
)

# ---------------------------------------------------------------------
# Mode alternatif "one-folder" (démarrage plus rapide, dossier au lieu
# d'un seul .exe) : commentez le bloc EXE ci-dessus et utilisez plutôt :
#
# exe = EXE(
#     pyz, a.scripts, [], exclude_binaries=True, name="MultiMiner",
#     debug=False, console=False, icon=icon_path if has_icon else None,
# )
# coll = COLLECT(
#     exe, a.binaries, a.zipfiles, a.datas, strip=False, upx=False,
#     name="MultiMiner",
# )
# ---------------------------------------------------------------------
