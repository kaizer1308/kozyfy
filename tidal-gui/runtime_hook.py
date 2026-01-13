"""
PyInstaller runtime hook for Kozyfy.
Ensures proper initialization on all Windows versions.
"""
import os
import sys

# Set up proper working directory
if getattr(sys, 'frozen', False):
    # Running as bundled exe
    exe_dir = os.path.dirname(sys.executable)
    os.chdir(exe_dir)
    
    # Ensure Python can find modules
    sys.path.insert(0, exe_dir)
    
    # Set SSL certificate environment variables
    try:
        import certifi
        os.environ['SSL_CERT_FILE'] = certifi.where()
        os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()
    except ImportError:
        pass

# Suppress VLC error output during initialization
os.environ.setdefault('VLC_VERBOSE', '-1')

# Windows-specific DPI awareness for better display scaling
if sys.platform == 'win32':
    try:
        import ctypes
        # Set DPI awareness for crisp rendering on high-DPI displays
        try:
            # Windows 10 1607+ (Anniversary Update)
            ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
        except:
            try:
                # Windows 8.1+
                ctypes.windll.shcore.SetProcessDpiAwareness(1)  # PROCESS_SYSTEM_DPI_AWARE
            except:
                try:
                    # Fallback for older Windows
                    ctypes.windll.user32.SetProcessDPIAware()
                except:
                    pass
    except:
        pass
