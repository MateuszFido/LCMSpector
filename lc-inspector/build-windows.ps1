# WINDOWS:
pyinstaller --name "LC-Inspector" --icon icon.icns --exclude-module torch --exclude-module matplotlib --exclude-module frozendict --exclude-module torchvision --exclude-module torchgen --exclude-module tqdm --exclude-module torchaudio --add-data "debug.yaml:."  --add-data "ui/logo.png:ui" --add-data "config.json:." --add-data "app.log:." --noconsole --onedir main.py
