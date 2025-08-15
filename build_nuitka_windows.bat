@echo off
REM build_nuitka_windows.bat
REM Windows Nuitka build script for LC-Inspector following the migration plan

echo Building LCMSpector with Nuitka for Windows...

cd lc-inspector\

REM Ensure dependencies are installed
echo Installing/updating Nuitka...
pip install --upgrade "nuitka[full]"
pip install imageio

REM Clean previous builds
echo Cleaning previous builds...
if exist dist\ rmdir /s /q dist\
if exist build\ rmdir /s /q build\

REM Run Nuitka build
echo Running Nuitka compilation...
python -m nuitka ^
    --standalone ^
    --onefile ^
    --enable-plugin=pyside6 ^
    --enable-plugin=numpy ^
    --windows-icon-from-ico=resources/icon.png ^
    --windows-company-name="ETH Zurich" ^
    --windows-product-name="LCMSpector" ^
    --windows-file-version="1.0.0" ^
    --windows-product-version="1.0.0" ^
    --include-data-file=config.json=config.json ^
    --include-data-file=ui/logo.png=ui/logo.png ^
    --include-data-file=resources/MoNA-export-All_LC-MS-MS_Orbitrap.msp=resources/MoNA-export-All_LC-MS-MS_Orbitrap.msp ^
    --include-data-file=resources/icon.ico=resources/icon.png ^
    --include-data-file=resources/logo.png=resources/logo.png ^
    --include-data-file=resources/logo300x40.png=resources/logo300x40.png ^
    --nofollow-import-to=matplotlib,torch,torchvision,frozendict,tqdm ^
    --python-flag=no_site ^
    --python-flag=-O ^
    --output-dir=dist ^
    --show-progress ^
    --assume-yes-for-downloads ^
    main.py

echo Build completed! Executable created at: dist\main.exe

REM Validate the build
echo Validating build...
if exist "dist\main.exe" (
    echo ✓ Executable created successfully
    
    REM Check file size
    for %%I in ("dist\main.exe") do set size=%%~zI
    set /a sizeMB=%size%/1024/1024
    echo ✓ Executable size: %sizeMB%MB
    
    REM Test execution with timeout
    echo Testing executable...
    timeout /t 5 /nobreak >nul
    "dist\main.exe" --app-info
    
    if errorlevel 1 (
        echo ✗ Executable test failed
        exit /b 1
    ) else (
        echo ✓ Executable test passed
    )
    
    REM Rename executable to final name
    echo Renaming executable to LCMSpector.exe...
    move "dist\main.exe" "dist\LCMSpector.exe"
    if exist "dist\LCMSpector.exe" (
        echo Executable renamed successfully
    ) else (
        echo  Failed to rename executable
        exit /b 1
    )
) else (
    echo ✗ Executable not created
    exit /b 1
)

echo ✓ Windows build validation completed successfully!

REM Display build info
echo.
echo Build Summary:
echo ==============
echo Contents of dist folder:
dir dist\
echo Executable size: %sizeMB%MB

REM Test resource verification
echo.
echo Testing resource availability...
python -c "import sys; sys.path.insert(0, '.'); from utils.resources import verify_resources; resources = verify_resources(); [print(f'{name}: {\"OK\" if info[\"exists\"] else \"MISSING\"}') for name, info in resources.items()]"

pause