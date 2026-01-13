import threading
import sys
import os

# Initialize VLC with proper error handling
_vlc = None
_vlc_error = None

def _init_vlc():
    """Initialize VLC with proper DLL path handling for Windows."""
    global _vlc, _vlc_error
    
    if _vlc is not None or _vlc_error is not None:
        return _vlc, _vlc_error
    
    try:
        # Try to use our dependency checker first
        try:
            from utils.dependencies import get_vlc_instance
            vlc_module, error = get_vlc_instance()
            if vlc_module:
                _vlc = vlc_module
                return _vlc, None
            else:
                _vlc_error = error
        except ImportError:
            pass
        
        # Fallback: Try direct import with common VLC paths
        if sys.platform == "win32":
            vlc_paths = [
                r"C:\Program Files\VideoLAN\VLC",
                r"C:\Program Files (x86)\VideoLAN\VLC",
                os.path.join(os.environ.get("PROGRAMFILES", ""), "VideoLAN", "VLC"),
            ]
            
            for path in vlc_paths:
                if path and os.path.exists(path):
                    plugins_path = os.path.join(path, "plugins")
                    if os.path.exists(plugins_path):
                        os.environ["VLC_PLUGIN_PATH"] = plugins_path
                    if hasattr(os, 'add_dll_directory'):
                        try:
                            os.add_dll_directory(path)
                        except:
                            pass
                    # Add to PATH
                    current_path = os.environ.get("PATH", "")
                    if path not in current_path:
                        os.environ["PATH"] = path + os.pathsep + current_path
                    break
        
        import vlc
        _vlc = vlc
        return _vlc, None
        
    except OSError as e:
        _vlc_error = f"VLC library not found: {str(e)}"
        return None, _vlc_error
    except Exception as e:
        _vlc_error = f"VLC import failed: {str(e)}"
        return None, _vlc_error


class PlaybackManager:
    def __init__(self):
        self.vlc_module, self.vlc_error = _init_vlc()
        self.instance = None
        self.player = None
        self.current_playing_id = None
        self.is_playing = False
        self.current_track_info = None
        self._vlc_available = False
        
        if self.vlc_module:
            try:
                self.instance = self.vlc_module.Instance('--no-xlib')
                self.player = self.instance.media_player_new()
                self._vlc_available = True
            except Exception as e:
                print(f"[PlaybackManager] Failed to create VLC instance: {e}")
                self._vlc_available = False
        else:
            print(f"[PlaybackManager] VLC not available: {self.vlc_error}")
    
    def is_vlc_available(self):
        """Check if VLC is available for playback."""
        return self._vlc_available

    def play(self, url, track_info):
        if not self._vlc_available:
            print("[PlaybackManager] Cannot play - VLC not available")
            return False
        
        try:
            self.player.stop()
            media = self.instance.media_new(url)
            self.player.set_media(media)
            self.player.play()
            
            self.current_playing_id = track_info["id"]
            self.current_track_info = track_info
            self.is_playing = True
            return True
        except Exception as e:
            print(f"[PlaybackManager] Play error: {e}")
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
        except Exception as e:
            print(f"[PlaybackManager] Toggle error: {e}")
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
        if not self._vlc_available:
            return
        try:
            self.player.audio_set_volume(int(value))
        except:
            pass

    def get_progress(self):
        """Returns (current_time_ms, total_length_ms, progress_float_0_to_1)"""
        if not self._vlc_available:
            return 0, 0, 0
        try:
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
