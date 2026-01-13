@echo off
REM Kozyfy Build Script for Windows
REM Creates a portable executable that works on any Windows PC

echo ========================================
echo Kozyfy Build Script
echo ========================================
echo.

REM Navigate to script directory
cd /d "%~dp0"

REM Check for Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://www.python.org/
    pause
    exit /b 1
)

echo [1/4] Installing/Updating Dependencies...
pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo [2/4] Cleaning previous build...
if exist "dist" rmdir /s /q dist
if exist "build\Kozyfy" rmdir /s /q "build\Kozyfy"

echo.
echo [3/4] Building executable...
pyinstaller Kozyfy.spec --clean
if errorlevel 1 (
    echo ERROR: Build failed
    pause
    exit /b 1
)

echo.
echo [4/4] Build complete!
echo.
echo ========================================
echo SUCCESS! 
echo ========================================
echo.
echo The executable is located at:
echo   dist\Kozyfy.exe
echo.
echo IMPORTANT: Users need to have these installed:
echo   - VLC Media Player (64-bit): https://www.videolan.org/vlc/
echo   - FFmpeg (for downloads): https://ffmpeg.org/download.html
echo.
echo The app will show a warning if dependencies are missing.
echo.

pause
