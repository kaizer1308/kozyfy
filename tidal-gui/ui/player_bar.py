import customtkinter as ctk
from .icons import create_icon

class PlayerBar(ctk.CTkFrame):
    def __init__(self, master, playback_manager, on_download_click, on_lyrics_click=None, **kwargs):
        super().__init__(master, **kwargs)
        self.playback_manager = playback_manager
        self.on_download_click = on_download_click
        self.on_lyrics_click = on_lyrics_click
        
        self.configure(fg_color="#1a1a1a", height=100, corner_radius=10)
        self.grid_columnconfigure(1, weight=1)

        self._create_ui()
        
        # Smooth progress tracking
        self._last_progress = 0
        self._target_progress = 0
        self._last_time_ms = 0
        self._track_length_ms = 0
        self._last_display_second = None
        self._last_total_time_ms = None
        self._last_slider_value = 0
        self._smooth_interval_ms = 33
        
        self._start_updater()
        self._start_smooth_slider()

    def _create_ui(self):
        # -- Left: Track Info & Art --
        self.info_frame_player = ctk.CTkFrame(self, fg_color="transparent")
        self.info_frame_player.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        
        self.art_label = ctk.CTkLabel(self.info_frame_player, text="🎵", width=60, height=60, fg_color="#333", corner_radius=5)
        self.art_label.pack(side="left", padx=(0, 10))
        
        self.text_frame_player = ctk.CTkFrame(self.info_frame_player, fg_color="transparent")
        self.text_frame_player.pack(side="left")
        
        self.lbl_title = ctk.CTkLabel(self.text_frame_player, text="Not Playing", font=("Arial", 14, "bold"), anchor="w", width=200)
        self.lbl_title.pack(anchor="w")
        
        self.lbl_artist = ctk.CTkLabel(self.text_frame_player, text="...", font=("Arial", 12), text_color="gray", anchor="w", width=200)
        self.lbl_artist.pack(anchor="w")

        self.lbl_meta = ctk.CTkLabel(self.text_frame_player, text="", font=("Arial", 10), text_color="#777777", anchor="w", width=240)
        self.lbl_meta.pack(anchor="w")

        # -- Center: Controls & Progress --
        self.controls_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.controls_frame.grid(row=0, column=1, padx=10, pady=5)
        
        # Prepare Icons
        self.icon_play = create_icon("play", size=(24, 24))
        self.icon_pause = create_icon("pause", size=(24, 24))
        self.icon_prev = create_icon("prev", size=(20, 20))
        self.icon_next = create_icon("next", size=(20, 20))

        # Buttons
        self.btns_frame = ctk.CTkFrame(self.controls_frame, fg_color="transparent")
        self.btns_frame.pack()
        
        self.btn_prev = ctk.CTkButton(self.btns_frame, text="", image=self.icon_prev, width=40, height=40, fg_color="transparent", border_width=1, state="disabled")
        self.btn_prev.pack(side="left", padx=5)
        
        self.btn_play = ctk.CTkButton(self.btns_frame, text="", image=self.icon_play, width=50, height=50, corner_radius=25, command=self.toggle_play)
        self.btn_play.pack(side="left", padx=10)
        
        self.btn_next = ctk.CTkButton(self.btns_frame, text="", image=self.icon_next, width=40, height=40, fg_color="transparent", border_width=1, state="disabled")
        self.btn_next.pack(side="left", padx=5)
        
        # Progress Bar
        self.progress_frame = ctk.CTkFrame(self.controls_frame, fg_color="transparent")
        self.progress_frame.pack(fill="x", pady=(5,0))
        
        self.lbl_current_time = ctk.CTkLabel(self.progress_frame, text="0:00", font=("Arial", 10), width=30)
        self.lbl_current_time.pack(side="left", padx=5)
        
        self.slider_progress = ctk.CTkSlider(self.progress_frame, width=300, height=10, from_=0, to=1, command=self.on_seek)
        self.slider_progress.set(0)
        self.slider_progress.pack(side="left", fill="x", expand=True)
        
        self.lbl_total_time = ctk.CTkLabel(self.progress_frame, text="0:00", font=("Arial", 10), width=30)
        self.lbl_total_time.pack(side="left", padx=5)

        # -- Right: Volume & Extras --
        self.extras_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.extras_frame.grid(row=0, column=2, padx=20, pady=10, sticky="e")
        
        # Lyrics Button
        self.icon_lyrics = create_icon("lyrics", size=(20, 20))
        self.btn_lyrics = ctk.CTkButton(
            self.extras_frame, 
            text="", 
            image=self.icon_lyrics,
            width=36, 
            height=36, 
            fg_color="transparent",
            hover_color="#333333",
            border_width=1,
            state="disabled", 
            command=self._on_lyrics_click
        )
        self.btn_lyrics.pack(side="left", padx=5)
        
        self.btn_dl_current = ctk.CTkButton(self.extras_frame, text="Download", width=80, height=24, state="disabled", command=self.download_current_track)
        self.btn_dl_current.pack(side="left", padx=10)
        
        self.lbl_vol = ctk.CTkLabel(self.extras_frame, text="🔊", font=("Arial", 12))
        self.lbl_vol.pack(side="left", padx=5)
        
        self.slider_vol = ctk.CTkSlider(self.extras_frame, width=100, height=15, from_=0, to=100, command=self.set_volume)
        self.slider_vol.set(100)
        self.slider_vol.pack(side="left")

    def toggle_play(self):
        is_playing = self.playback_manager.toggle()
        if is_playing:
            self.btn_play.configure(image=self.icon_pause)
        else:
            self.btn_play.configure(image=self.icon_play)

    def set_volume(self, value):
        self.playback_manager.set_volume(value)

    def on_seek(self, value):
        self.playback_manager.seek(value)

    def download_current_track(self):
        if self.playback_manager.current_track_info:
            self.on_download_click(self.playback_manager.current_track_info)

    def _on_lyrics_click(self):
        """Handle lyrics button click."""
        if self.on_lyrics_click:
            self.on_lyrics_click()

    def update_track_info(self, track_info, cover_image):
        self.lbl_title.configure(text=track_info["title"])
        self.lbl_artist.configure(text=track_info["artist"])

        meta_parts = []
        album = track_info.get("album")
        if album:
            meta_parts.append(album)
        quality_detail = track_info.get("quality_detail")
        if quality_detail:
            meta_parts.append(quality_detail)
        self.lbl_meta.configure(text=" • ".join(meta_parts))
        
        if cover_image:
            self.art_label.configure(image=cover_image, text="")
        else:
            self.art_label.configure(image=None, text="🎵")
            
        self.btn_dl_current.configure(state="normal")
        self.btn_lyrics.configure(state="normal")
        self.btn_play.configure(image=self.icon_pause)
        self._last_display_second = None
        self._last_total_time_ms = None
        self._last_slider_value = 0
        self._last_progress = 0
        self._target_progress = 0
        self._track_length_ms = 0

    def _start_updater(self):
        """Fetch actual position from VLC at lower frequency."""
        def fmt_time(ms):
            s = ms // 1000
            m = s // 60
            s = s % 60
            return f"{m}:{s:02d}"

        curr, length, prog = self.playback_manager.get_progress()
        if length > 0:
            self._target_progress = prog
            self._last_time_ms = curr
            self._track_length_ms = length
            current_second = curr // 1000
            if current_second != self._last_display_second:
                self.lbl_current_time.configure(text=fmt_time(curr))
                self._last_display_second = current_second
            if length != self._last_total_time_ms:
                self.lbl_total_time.configure(text=fmt_time(length))
                self._last_total_time_ms = length
        
        # Update actual position every 200ms (VLC polling)
        self.after(200, self._start_updater)
    
    def _start_smooth_slider(self):
        """Interpolate slider position at 60fps for smooth animation."""
        delay_ms = 200
        if self._track_length_ms > 0 and self.playback_manager.is_playing:
            # Interpolate: estimate current position based on time elapsed
            # This creates smooth motion between VLC position updates
            
            # Smoothly lerp towards target
            diff = self._target_progress - self._last_progress
            
            # Use easing for smoother feel (lerp factor)
            if abs(diff) > 0.01:
                # Larger jump - snap faster (seeking)
                self._last_progress += diff * 0.3
            else:
                # Normal playback - smooth interpolation
                # Add estimated progress based on frame time
                estimated_advance = self._smooth_interval_ms / self._track_length_ms
                self._last_progress += estimated_advance
                
                # Also lerp towards actual target to stay synced
                self._last_progress += (self._target_progress - self._last_progress) * 0.1
            
            # Clamp to valid range
            self._last_progress = max(0, min(1, self._last_progress))
            if abs(self._last_progress - self._last_slider_value) > 0.001:
                self._last_slider_value = self._last_progress
                self.slider_progress.set(self._last_progress)
            delay_ms = self._smooth_interval_ms
        elif self._track_length_ms > 0:
            # Paused - just sync to target
            self._last_progress = self._target_progress
            if abs(self._last_progress - self._last_slider_value) > 0.001:
                self._last_slider_value = self._last_progress
                self.slider_progress.set(self._last_progress)
            delay_ms = 150
        else:
            delay_ms = 250
        
        self.after(delay_ms, self._start_smooth_slider)
