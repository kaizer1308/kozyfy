"""
Cross-platform path utilities for PyInstaller bundled applications.
Ensures paths work correctly whether running from source or as a compiled exe.
"""
import os
import sys
import tempfile

def get_app_dir():
    """
    Get the application directory.
    - For bundled exe: Returns the directory containing the exe
    - For source: Returns the directory containing the main script
    """
    if getattr(sys, 'frozen', False):
        # Running as compiled exe
        return os.path.dirname(sys.executable)
    else:
        # Running from source
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_resource_path(relative_path):
    """
    Get absolute path to resource, works for dev and for PyInstaller.
    """
    if getattr(sys, 'frozen', False):
        # Running as compiled exe - resources are in _MEIPASS
        base_path = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    else:
        # Running from source
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    return os.path.join(base_path, relative_path)

def get_temp_dir():
    """
    Get a writable temp directory that works across all Windows versions.
    Uses system temp directory to avoid permission issues.
    """
    # Create app-specific temp folder
    app_temp = os.path.join(tempfile.gettempdir(), "Kozyfy")
    os.makedirs(app_temp, exist_ok=True)
    return app_temp

def get_default_download_dir():
    """
    Get a sensible default download directory that works across Windows versions.
    Falls back to user's home directory if other options fail.
    """
    # Try user's Music folder first
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                           r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders") as key:
            music_dir = winreg.QueryValueEx(key, "My Music")[0]
            if os.path.exists(music_dir):
                kozyfy_music = os.path.join(music_dir, "Kozyfy Downloads")
                os.makedirs(kozyfy_music, exist_ok=True)
                return kozyfy_music
    except:
        pass
    
    # Try standard Music folder
    music_folder = os.path.join(os.path.expanduser("~"), "Music", "Kozyfy Downloads")
    try:
        os.makedirs(music_folder, exist_ok=True)
        return music_folder
    except:
        pass
    
    # Fall back to Documents
    docs_folder = os.path.join(os.path.expanduser("~"), "Documents", "Kozyfy Downloads")
    try:
        os.makedirs(docs_folder, exist_ok=True)
        return docs_folder
    except:
        pass
    
    # Last resort: user home directory
    home_folder = os.path.join(os.path.expanduser("~"), "Kozyfy Downloads")
    os.makedirs(home_folder, exist_ok=True)
    return home_folder

def get_config_dir():
    """
    Get the configuration directory for storing app settings.
    Uses APPDATA on Windows for proper user data storage.
    """
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA", os.path.expanduser("~"))
        config_dir = os.path.join(appdata, "Kozyfy")
    else:
        config_dir = os.path.join(os.path.expanduser("~"), ".kozyfy")
    
    os.makedirs(config_dir, exist_ok=True)
    return config_dir

def is_bundled():
    """Check if running as a PyInstaller bundle."""
    return getattr(sys, 'frozen', False)
