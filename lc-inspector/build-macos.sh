#!/bin/bash
# MACOS .APP:
pyinstaller --name "LC-Inspector" --icon icon.icns --exclude-module torch --exclude-module matplotlib --exclude-module frozendict --exclude-module torchvision --exclude-module torchgen --exclude-module tqdm --exclude-module torchaudio --add-data "debug.yaml:."  --add-data "ui/logo.png:ui" --add-data "config.json:." --add-data "app.log:." --windowed main.py

# TO MAKE A .DMG:
# Disk utility -> File -> New image -> Blank image -> sparse bundle disk image -> save 
# Copy .app into sparsebundle
# Set icon view
# Set background image (right-click -> Show view options) 
# Set as defaults
# Make a symlink to Applications (ln -s /Applications /Volumes/volumename)

