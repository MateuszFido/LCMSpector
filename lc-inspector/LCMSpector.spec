# PyInstaller spec for LCMSpector
# - Adds macOS-specific fixes to prevent Qt6 permission plugin crashes
# - Injects Info.plist privacy keys (location) on macOS
# - Adds qt.conf next to the macOS executable to stabilize Qt path resolution
# - Leaves Windows packaging behavior unchanged relative to your current CLI flags

import os
import sys
from PyInstaller.utils.hooks import copy_metadata
from PyInstaller.building.build_main import Analysis, PYZ, EXE, COLLECT, BUNDLE

BASE_DIR = os.path.abspath(os.path.dirname(sys.argv[0]))
is_mac = sys.platform == "darwin"
is_win = sys.platform == "win32"

# Prepare qt.conf only for macOS so it lands next to Contents/MacOS/LCMSpector
datas = [
    ("ui/logo.png", "ui"),
    ("config.json", "."),
    ("app.log", "."),
    ("resources/MoNA-export-All_LC-MS-MS_Orbitrap.msp", "resources"),
]
if is_mac:
    qt_conf_path = os.path.join(BASE_DIR, "qt.conf")
    if not os.path.exists(qt_conf_path):
        with open(qt_conf_path, "w", encoding="utf-8") as f:
            f.write(
                "[Paths]\n"
                "Plugins = PlugIns\n"
                "Imports = Resources/qml\n"
                "Translations = Resources/translations\n"
            )
    datas.append(("qt.conf", "."))  # Placed next to the executable (Contents/MacOS)

# Exclude heavy/unneeded modules (same as your CLI flags)
excludes = [
    "torch",
    "matplotlib",
    "frozendict",
    "torchvision",
    "torchgen",
    "tqdm",
    "torchaudio",
]

# Collect package metadata if needed (safe no-op if missing)
metadata = []
for pkg in []:
    metadata += copy_metadata(pkg)

a = Analysis(
    ["main.py"],
    pathex=[BASE_DIR],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

# Create the executable (GUI, no console) similar to --noconsole/--windowed
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="LCMSpector",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    console=False,
    # Keep icon.icns to preserve current behavior; it is ignored on Windows.
    icon=os.path.join(BASE_DIR, "icon.icns"),
)

if is_mac:
    # Info.plist keys required to prevent crashes if Qt touches CoreLocation
    info_plist = {
        "CFBundleName": "LCMSpector",
        "CFBundleDisplayName": "LCMSpector",
        "CFBundleShortVersionString": "0.0.0",
        "CFBundleVersion": "0.0.0",
        "NSHighResolutionCapable": True,
        "NSLocationWhenInUseUsageDescription": "LCMSpector may initialize platform services provided by Qt that require location permissions.",
        "NSLocationAlwaysAndWhenInUseUsageDescription": "LCMSpector may initialize platform services provided by Qt that require location permissions.",
    }

    app = BUNDLE(
        exe,
        name="LCMSpector.app",
        icon=os.path.join(BASE_DIR, "icon.icns"),
        bundle_identifier="com.mateuszfido.lcmspector",
        info_plist=info_plist,
    )

    # Optional extra safeguard: remove the Darwin permissions plugin if you never request permissions.
    # Uncomment the following block if you want to exclude it.
    # from PyInstaller.building.toc import TOC
    # a.binaries = TOC([b for b in a.binaries if "libqdarwinpermissionplugin" not in b[0]])

else:
    # Windows (and others) one-folder layout exactly like your current CLI outcome
    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name="LCMSpector",
    )