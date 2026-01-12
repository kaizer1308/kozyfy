import vlc
import threading

class PlaybackManager:
    def __init__(self):
        self.instance = vlc.Instance()
        self.player = self.instance.media_player_new()
        self.current_playing_id = None
        self.is_playing = False
        self.current_track_info = None

    def play(self, url, track_info):
        self.player.stop()
        media = self.instance.media_new(url)
        self.player.set_media(media)
        self.player.play()
        
        self.current_playing_id = track_info["id"]
        self.current_track_info = track_info
        self.is_playing = True

    def toggle(self):
        if not self.current_playing_id:
            return False
            
        if self.player.is_playing():
            self.player.pause()
            self.is_playing = False
        else:
            self.player.play()
            self.is_playing = True
        return self.is_playing

    def stop(self):
        self.player.stop()
        self.is_playing = False

    def set_volume(self, value):
        self.player.audio_set_volume(int(value))

    def get_progress(self):
        """Returns (current_time_ms, total_length_ms, progress_float_0_to_1)"""
        if self.is_playing and self.player.is_playing():
            length = self.player.get_length()
            current = self.player.get_time()
            if length > 0:
                return current, length, current / length
        return 0, 0, 0

    def seek(self, percentage):
        length = self.player.get_length()
        if length > 0:
            target_time = int(percentage * length)
            self.player.set_time(target_time)

    def is_active(self):
        return self.player.is_playing()
