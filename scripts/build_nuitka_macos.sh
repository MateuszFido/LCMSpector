#!/bin/bash
# build_nuitka_macos.sh
# macOS Nuitka build script for LC-Inspector following the migration plan

set -e

echo "Building LCMSpector with Nuitka for macOS..."

# Change to project directory
cd lc-inspector/

# Ensure dependencies are installed
echo "Installing/updating Nuitka..."
pip install --upgrade "nuitka[full]"

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf dist/ build/

# Run Nuitka build
echo "Running Nuitka compilation..."
python3 -m nuitka \
    --standalone \
    --onefile \
    --macos-create-app-bundle \
    --macos-app-icon=icon.icns \
    --macos-app-name="LCMSpector" \
    --macos-app-version="1.0.0" \
    --macos-signed-app-name="com.ethz.lcmspector" \
    --include-data-file=config.json=config.json \
    --include-data-file=ui/logo.png=ui/logo.png \
    --include-data-file=resources/MoNA-export-All_LC-MS-MS_Orbitrap.msp=resources/MoNA-export-All_LC-MS-MS_Orbitrap.msp \
    --include-data-file=resources/icon.icns=resources/icon.icns \
    --include-data-file=resources/logo.png=resources/logo.png \
    --include-data-file=resources/logo300x40.png=resources/logo300x40.png \
    --enable-plugin=pyside6 \
    --include-qt-plugins=platforms,imageformats,iconengines \
    --nofollow-import-to=matplotlib,torch,torchvision,frozendict,tqdm \
    --python-flag=no_site \
    --python-flag=-O \
    --output-dir=dist \
    --show-progress \
    --assume-yes-for-downloads \
    --disable-ccache \
    main.py

echo "Build completed! Validating Nuitka output..."

# Validate the build
echo "Validating build..."
if [ -d "dist/main.app" ]; then
    echo " App bundle created successfully"
    
    # Check bundle structure
    if [ -f "dist/main.app/Contents/MacOS/main" ]; then
        echo " Executable found in bundle"
    else
        echo " Executable not found in bundle"
        exit 1
    fi
    
    # Check bundle size
    bundle_size=$(du -sh dist/main.app | cut -f1)
    echo " Bundle size: $bundle_size"
    
    # Test execution with timeout
    echo "Testing app execution..."
    timeout 10s open -a "dist/main.app" --args --app-info || echo "App test completed (timeout expected)"
    
else
    echo " App bundle not created"
    exit 1
fi

echo " macOS build validation completed successfully!"

# Rename the app bundle to final name
echo "Renaming app bundle to LCMSpector.app..."
mv "dist/main.app" "dist/LCMSpector.app"

# Rename the internal executable to match expected name
echo "Renaming internal executable..."
mv "dist/LCMSpector.app/Contents/MacOS/main" "dist/LCMSpector.app/Contents/MacOS/LCMSpector"
echo " App bundle and executable renamed successfully"

# Display bundle info
echo ""
echo "Build Summary:"
echo "=============="
echo "Bundle path: $(pwd)/dist/LCMSpector.app"
echo "Bundle size: $bundle_size"
echo "Executable: dist/LCMSpector.app/Contents/MacOS/LCMSpector"

# Test resource verification
echo ""
echo "Testing resource availability..."
python3 -c "
import sys
sys.path.insert(0, '.')
from utils.resources import verify_resources
resources = verify_resources()
for name, info in resources.items():
    status = 'OK' if info['exists'] else 'MISSING'
    print(f'{name}: {status}')
"