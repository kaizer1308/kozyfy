# Kozyfy - Tidal GUI Client

A modern desktop application for streaming and downloading from Tidal.

## Requirements

### For Running the Application

The following software must be installed on the user's computer:

1. **VLC Media Player (64-bit)** - Required for audio playback
   - Download: https://www.videolan.org/vlc/
   - Make sure to install the **64-bit version**

2. **FFmpeg** - Required for downloading tracks
   - Download: https://ffmpeg.org/download.html
   - Must be added to system PATH

### For Building from Source

- Python 3.8 or higher
- All packages listed in `requirements.txt`

## Installation

### Option 1: Pre-built Executable

1. Download `Kozyfy.exe` from the releases
2. Install VLC Media Player (64-bit)
3. Install FFmpeg and add to PATH
4. Run `Kozyfy.exe`

### Option 2: Build from Source

1. Clone the repository
2. Navigate to the `tidal-gui` folder
3. Run `build.bat` (Windows)

Or manually:
```bash
pip install -r requirements.txt
pyinstaller Kozyfy.spec --clean
```

The executable will be created at `dist/Kozyfy.exe`

## Features

- Search for tracks and albums
- Stream music in various qualities (Hi-Res, Lossless, High, Low)
- Download tracks with embedded metadata and cover art
- Download entire albums
- Quality filtering for search results
- Persistent settings

## Supported Windows Versions

- Windows 10 (all versions)
- Windows 11 (all versions)
- Windows 8.1 (limited testing)

## Troubleshooting

### "VLC Not Found" Error
- Install VLC Media Player 64-bit version
- Restart the application after installation

### "FFmpeg Not Found" Error
- Download FFmpeg from https://ffmpeg.org/download.html
- Extract to a folder (e.g., `C:\ffmpeg`)
- Add the `bin` folder to your system PATH:
  1. Search "Environment Variables" in Windows
  2. Click "Environment Variables"
  3. Under "System Variables", find "Path"
  4. Click "Edit" and add `C:\ffmpeg\bin`
  5. Click OK and restart the application

### Application Won't Start
- Make sure you have the Microsoft Visual C++ Redistributable installed
- Download from: https://aka.ms/vs/17/release/vc_redist.x64.exe

### SSL/Connection Errors
- Check your internet connection
- Try a different API URL in Settings

## Configuration

Settings are stored in `%APPDATA%\Kozyfy\`

Default download location: `Music\Kozyfy Downloads`

## License

See LICENSE file for details.
