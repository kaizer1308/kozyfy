"""
Dependency checker and bundled binary manager.
Handles FFmpeg and VLC detection with proper error messages.
"""
import os
import sys
import subprocess
import shutil
from .paths import get_resource_path, is_bundled, get_app_dir

# Store paths once found to avoid repeated lookups
_ffmpeg_path = None
_vlc_path = None

def get_ffmpeg_path():
    """
    Get the path to ffmpeg executable.
    Checks bundled location first, then system PATH.
    Returns None if not found.
    """
    global _ffmpeg_path
    if _ffmpeg_path is not None:
        return _ffmpeg_path
    
    # Check if bundled with the app
    if is_bundled():
        bundled_paths = [
            os.path.join(get_app_dir(), "ffmpeg.exe"),
            os.path.join(get_app_dir(), "ffmpeg", "ffmpeg.exe"),
            os.path.join(get_app_dir(), "bin", "ffmpeg.exe"),
        ]
        for path in bundled_paths:
            if os.path.exists(path):
                _ffmpeg_path = path
                return _ffmpeg_path
    
    # Check system PATH
    ffmpeg_in_path = shutil.which("ffmpeg")
    if ffmpeg_in_path:
        _ffmpeg_path = ffmpeg_in_path
        return _ffmpeg_path
    
    # Check common installation locations on Windows
    common_paths = [
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe",
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "ffmpeg", "bin", "ffmpeg.exe"),
        os.path.join(os.environ.get("PROGRAMFILES", ""), "ffmpeg", "bin", "ffmpeg.exe"),
    ]
    
    for path in common_paths:
        if path and os.path.exists(path):
            _ffmpeg_path = path
            return _ffmpeg_path
    
    return None

def check_ffmpeg():
    """
    Check if ffmpeg is available and working.
    Returns (success: bool, path_or_error: str)
    """
    ffmpeg = get_ffmpeg_path()
    if not ffmpeg:
        return False, "FFmpeg not found. Please install FFmpeg and add it to your PATH."
    
    try:
        # Test if ffmpeg actually works
        result = subprocess.run(
            [ffmpeg, "-version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        )
        if result.returncode == 0:
            return True, ffmpeg
        else:
            return False, f"FFmpeg found but returned error code {result.returncode}"
    except subprocess.TimeoutExpired:
        return False, "FFmpeg found but timed out during version check"
    except Exception as e:
        return False, f"FFmpeg check failed: {str(e)}"

def get_vlc_instance():
    """
    Get a VLC instance with proper library path handling.
    Returns (vlc_module, error_message)
    """
    global _vlc_path
    
    # Suppress VLC error dialogs
    os.environ['VLC_VERBOSE'] = '-1'
    
    # Try to set VLC plugin path before import
    vlc_paths = [
        r"C:\Program Files\VideoLAN\VLC",
        r"C:\Program Files (x86)\VideoLAN\VLC",
        os.path.join(os.environ.get("PROGRAMFILES", ""), "VideoLAN", "VLC"),
        os.path.join(os.environ.get("PROGRAMFILES(X86)", ""), "VideoLAN", "VLC"),
    ]
    
    # Find VLC installation - verify libvlc.dll exists
    for path in vlc_paths:
        if path and os.path.exists(path):
            libvlc = os.path.join(path, "libvlc.dll")
            if os.path.exists(libvlc):
                _vlc_path = path
                plugins_path = os.path.join(path, "plugins")
                if os.path.exists(plugins_path):
                    os.environ["VLC_PLUGIN_PATH"] = plugins_path
                # Add VLC to DLL search path
                if hasattr(os, 'add_dll_directory'):
                    try:
                        os.add_dll_directory(path)
                    except:
                        pass
                break
    
    # Also try adding to PATH
    if _vlc_path:
        current_path = os.environ.get("PATH", "")
        if _vlc_path not in current_path:
            os.environ["PATH"] = _vlc_path + os.pathsep + current_path
    
    try:
        import vlc
        # Test that we can create an instance with safe options
        instance = vlc.Instance('--quiet', '--no-plugins-cache')
        if instance:
            return vlc, None
        else:
            return None, "VLC instance creation failed"
    except OSError as e:
        error_str = str(e).lower()
        if "entry point" in error_str or "procedure" in error_str:
            return None, "VLC version mismatch. Please update VLC to the latest 64-bit version."
        elif "cannot load" in error_str or "not found" in error_str:
            return None, "VLC is not installed. Please install VLC media player (64-bit recommended)."
        return None, f"VLC error: {str(e)}"
    except Exception as e:
        return None, f"VLC import failed: {str(e)}"

def check_vlc():
    """
    Check if VLC is available and working.
    Returns (success: bool, error_message: str or None)
    NOTE: This does a light check without loading VLC to avoid DLL errors.
    """
    # Just check if VLC is installed, don't try to load it
    vlc_paths = [
        r"C:\Program Files\VideoLAN\VLC",
        r"C:\Program Files (x86)\VideoLAN\VLC",
        os.path.join(os.environ.get("PROGRAMFILES", ""), "VideoLAN", "VLC"),
        os.path.join(os.environ.get("PROGRAMFILES(X86)", ""), "VideoLAN", "VLC"),
    ]
    
    for path in vlc_paths:
        if path and os.path.exists(path):
            libvlc = os.path.join(path, "libvlc.dll")
            if os.path.exists(libvlc):
                return True, None
    
    return False, "VLC Media Player not found. Please install VLC (64-bit)."

def check_all_dependencies():
    """
    Check all required dependencies.
    Returns dict with status of each dependency.
    """
    results = {
        "ffmpeg": {"ok": False, "path": None, "error": None},
        "vlc": {"ok": False, "error": None}
    }
    
    # Check FFmpeg
    ffmpeg_ok, ffmpeg_result = check_ffmpeg()
    results["ffmpeg"]["ok"] = ffmpeg_ok
    if ffmpeg_ok:
        results["ffmpeg"]["path"] = ffmpeg_result
    else:
        results["ffmpeg"]["error"] = ffmpeg_result
    
    # Check VLC
    vlc_ok, vlc_error = check_vlc()
    results["vlc"]["ok"] = vlc_ok
    if not vlc_ok:
        results["vlc"]["error"] = vlc_error
    
    return results

def get_missing_dependencies_message():
    """
    Get a user-friendly message about missing dependencies.
    Returns None if all dependencies are satisfied.
    """
    deps = check_all_dependencies()
    missing = []
    
    if not deps["ffmpeg"]["ok"]:
        missing.append(f"• FFmpeg: {deps['ffmpeg']['error']}")
    
    if not deps["vlc"]["ok"]:
        missing.append(f"• VLC: {deps['vlc']['error']}")
    
    if missing:
        msg = "Missing Dependencies:\n\n" + "\n\n".join(missing)
        msg += "\n\nPlease install the missing software and restart the application."
        msg += "\n\nDownload links:"
        msg += "\n• FFmpeg: https://ffmpeg.org/download.html"
        msg += "\n• VLC (64-bit): https://www.videolan.org/vlc/"
        return msg
    
    return None
