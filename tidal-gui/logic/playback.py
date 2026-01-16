import threading
import sys
import os
import logging

logger = logging.getLogger("kozyfy.playback")

# VLC is loaded lazily to prevent DLL errors on startup
_vlc = None
_vlc_error = None
_vlc_initialized = False

def _init_vlc():
    """Initialize VLC with proper DLL path handling for Windows."""
    global _vlc, _vlc_error, _vlc_initialized
    
    if _vlc_initialized:
        return _vlc, _vlc_error
    
    _vlc_initialized = True
    
    try:
        # Suppress VLC error dialogs and logging
        os.environ['VLC_VERBOSE'] = '-1'
        
        # On Windows, we need to be very careful about VLC initialization
        if sys.platform == "win32":
            # Find VLC installation
            vlc_paths = [
                r"C:\Program Files\VideoLAN\VLC",
                r"C:\Program Files (x86)\VideoLAN\VLC",
                os.path.join(os.environ.get("PROGRAMFILES", ""), "VideoLAN", "VLC"),
                os.path.join(os.environ.get("PROGRAMFILES(X86)", ""), "VideoLAN", "VLC"),
            ]
            
            vlc_path = None
            for path in vlc_paths:
                if path and os.path.exists(path) and os.path.exists(os.path.join(path, "libvlc.dll")):
                    vlc_path = path
                    break
            
            if vlc_path:
                # Set plugin path BEFORE importing vlc
                plugins_path = os.path.join(vlc_path, "plugins")
                if os.path.exists(plugins_path):
                    os.environ["VLC_PLUGIN_PATH"] = plugins_path
                
                # Add VLC to DLL search path (Python 3.8+)
                if hasattr(os, 'add_dll_directory'):
                    try:
                        os.add_dll_directory(vlc_path)
                    except Exception:
                        pass
                
                # Also add to PATH as fallback
                current_path = os.environ.get("PATH", "")
                if vlc_path not in current_path:
                    os.environ["PATH"] = vlc_path + os.pathsep + current_path
            else:
                _vlc_error = "VLC Media Player not found. Please install VLC (64-bit) from https://www.videolan.org/vlc/"
                return None, _vlc_error
        
        # Now try to import VLC
        import vlc
        
        # Test that we can create an instance with minimal plugins
        # Use --no-plugins-cache to avoid stale plugin issues
        # Use --quiet to suppress errors
        instance = vlc.Instance('--no-xlib', '--quiet', '--no-plugins-cache')
        if instance:
            _vlc = vlc
            return _vlc, None
        else:
            _vlc_error = "Failed to create VLC instance"
            return None, _vlc_error
            
    except OSError as e:
        error_str = str(e).lower()
        if "entry point" in error_str or "procedure" in error_str:
            _vlc_error = "VLC version mismatch. Please update VLC to the latest version (64-bit) from https://www.videolan.org/vlc/"
        elif "cannot load" in error_str or "not found" in error_str:
            _vlc_error = "VLC is not installed. Please install VLC (64-bit) from https://www.videolan.org/vlc/"
        else:
            _vlc_error = f"VLC error: {str(e)}"
        return None, _vlc_error
    except Exception as e:
        _vlc_error = f"VLC initialization failed: {str(e)}"
        return None, _vlc_error


class PlaybackManager:
    def __init__(self):
        # Don't initialize VLC in constructor - do it lazily
        self.vlc_module = None
        self.vlc_error = None
        self.instance = None
        self.player = None
        self.current_playing_id = None
        self.is_playing = False
        self.current_track_info = None
        self._vlc_available = None  # None = not checked yet
        self.volume = 100
        self.on_track_end = None
        self._end_notified = False
    
    def _ensure_vlc(self):
        """Lazy initialization of VLC - only when actually needed."""
        if self._vlc_available is not None:
            return self._vlc_available
        
        self.vlc_module, self.vlc_error = _init_vlc()
        
        if self.vlc_module:
            try:
                self.instance = self.vlc_module.Instance('--no-xlib', '--quiet')
                self.player = self.instance.media_player_new()
                self.player.audio_set_volume(int(self.volume))
                self._vlc_available = True
                logger.info("VLC initialized successfully")
            except Exception:
                logger.exception("Failed to create VLC instance")
                self._vlc_available = False
                self.vlc_error = "Failed to create VLC instance"
        else:
            logger.error("VLC not available: %s", self.vlc_error)
            self._vlc_available = False
        
        return self._vlc_available
    
    def is_vlc_available(self):
        """Check if VLC is available for playback."""
        return self._ensure_vlc()
    
    def get_vlc_error(self):
        """Get the VLC error message if not available."""
        self._ensure_vlc()
        return self.vlc_error

    def set_on_track_end(self, callback):
        """Register a callback invoked when the current track ends."""
        self.on_track_end = callback

    def play(self, url, track_info):
        if not self._vlc_available:
            logger.warning("Cannot play - VLC not available")
            return False
        
        try:
            self.player.stop()
            media = self.instance.media_new(url)
            self.player.set_media(media)
            self.player.play()
            
            self.current_playing_id = track_info["id"]
            self.current_track_info = track_info
            self.is_playing = True
            self._end_notified = False
            return True
        except Exception:
            logger.exception("Playback start failed")
            return False

    def toggle(self):
        if not self._vlc_available or not self.current_playing_id:
            return False
        
        try:
            if self.player.is_playing():
                self.player.pause()
                self.is_playing = False
            else:
                self.player.play()
                self.is_playing = True
            return self.is_playing
        except Exception:
            logger.exception("Playback toggle failed")
            return False

    def stop(self):
        if not self._vlc_available:
            return
        try:
            self.player.stop()
        except:
            pass
        self.is_playing = False

    def set_volume(self, value):
        self.volume = int(value)
        if not self._vlc_available:
            return
        try:
            self.player.audio_set_volume(self.volume)
        except:
            pass

    def get_progress(self):
        """Returns (current_time_ms, total_length_ms, progress_float_0_to_1)"""
        if not self._vlc_available:
            return 0, 0, 0
        try:
            if self.vlc_module and self.player:
                state = self.player.get_state()
                if state == self.vlc_module.State.Ended:
                    if not self._end_notified:
                        self.is_playing = False
                        self._end_notified = True
                        if self.on_track_end:
                            self.on_track_end()
                    return 0, 0, 0
            if self.is_playing and self.player.is_playing():
                length = self.player.get_length()
                current = self.player.get_time()
                if length > 0:
                    return current, length, current / length
        except:
            pass
        return 0, 0, 0

    def seek(self, percentage):
        if not self._vlc_available:
            return
        try:
            length = self.player.get_length()
            if length > 0:
                target_time = int(percentage * length)
                self.player.set_time(target_time)
        except:
            pass

    def is_active(self):
        if not self._vlc_available:
            return False
        try:
            return self.player.is_playing()
        except:
            return False
