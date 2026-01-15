import customtkinter as ctk

class SearchResultsView(ctk.CTkScrollableFrame):
    def __init__(self, master, on_play, on_download, **kwargs):
        super().__init__(master, label_text="Results", **kwargs)
        self.on_play = on_play
        self.on_download = on_download
        self._pending_items = []
        self._render_job = None
        self._render_batch_size = 20

    def clear(self):
        if self._render_job is not None:
            self.after_cancel(self._render_job)
            self._render_job = None
        self._pending_items = []
        for widget in self.winfo_children():
            widget.destroy()

    def display_message(self, message):
        self.clear()
        ctk.CTkLabel(self, text=message).pack(pady=20)

    def populate(self, items):
        self.clear()
        self._pending_items = list(items)
        self._render_next_batch()

    def _render_next_batch(self):
        if not self._pending_items:
            self._render_job = None
            return

        batch_count = min(self._render_batch_size, len(self._pending_items))
        for _ in range(batch_count):
            item = self._pending_items.pop(0)
            self._create_row(item)

        if self._pending_items:
            self._render_job = self.after(1, self._render_next_batch)
        else:
            self._render_job = None

    def _create_row(self, item):
        item_type = item.get("_type", "TRACK")
        item_id = item.get("id")
        title = item.get("title", "Unknown")
        
        # Artist handling
        artist = item.get("artist", {}).get("name")
        if not artist and "artists" in item:
            # Join multiple artists
            artist = ", ".join([a.get("name", "") for a in item["artists"]])
        if not artist:
            artist = "Unknown Artist"
        
        # Parse Quality
        quality = item.get("audioQuality", "UNKNOWN")
        tags = item.get("mediaMetadata", {}).get("tags", [])
        audio_modes = item.get("audioModes") or []
        
        display_quality = quality
        if "HIRES_LOSSLESS" in tags:
             display_quality = "Hi-Res Lossless"
        elif "MQA" in tags:
             display_quality = "Master (MQA)"
        elif "DOLBY_ATMOS" in tags:
             display_quality = "Dolby Atmos"
        elif quality == "HI_RES":
             display_quality = "Hi-Res"
        elif quality == "LOSSLESS":
             display_quality = "Lossless"

        quality_extras = []
        if "MQA" in tags:
            quality_extras.append("MQA")
        if "DOLBY_ATMOS" in tags:
            quality_extras.append("Dolby Atmos")
        if "SONY_360RA" in tags:
            quality_extras.append("360 Reality Audio")
        if audio_modes:
            quality_extras.append("/".join(audio_modes).title())

        quality_parts = [display_quality] if display_quality else []
        quality_parts.extend(quality_extras)
        quality_detail = " • ".join(quality_parts) if quality_parts else "Unknown"
             
        # Quality Color
        q_color = "gray"
        if "Hi-Res" in display_quality or "Master" in display_quality:
            q_color = "#FFA500" # Gold/Orange
        elif "Lossless" in display_quality:
            q_color = "#00BFFF" # Blue

        row_frame = ctk.CTkFrame(self)
        row_frame.pack(fill="x", pady=2)
        
        # Info Group
        info_frame = ctk.CTkFrame(row_frame, fg_color="transparent")
        info_frame.pack(side="left", padx=10, pady=5, fill="x", expand=True)
        
        title_lbl = ctk.CTkLabel(info_frame, text=title, font=("Arial", 13, "bold"), anchor="w")
        title_lbl.pack(fill="x")
        
        if item_type == "ALBUM":
            release_date = item.get("releaseDate", "")
            tracks_count = item.get("numberOfTracks", 0)
            sub_text = f"Album • {artist} • {tracks_count} Tracks • {release_date}"
            
            sub_lbl = ctk.CTkLabel(info_frame, text=sub_text, font=("Arial", 11), text_color="gray", anchor="w")
            sub_lbl.pack(fill="x")
            
            qual_lbl = ctk.CTkLabel(
                row_frame,
                text=quality_detail,
                text_color=q_color,
                font=("Arial", 11, "bold"),
                width=150,
                anchor="e",
                justify="right",
                wraplength=150
            )
            qual_lbl.pack(side="right", padx=(5, 10))

            # Download Button (Album)
            dl_btn = ctk.CTkButton(row_frame, text="Download", width=80, height=28,
                                   command=lambda: self.on_download(item_id, f"{artist} - {title}", "ALBUM"))
            dl_btn.pack(side="right", padx=10, pady=5)
            
        else: # TRACK
            album = item.get("album", {}).get("title", "Unknown Album")
            duration = item.get("duration", 0)
            
            # Format duration
            mins = int(duration / 60)
            secs = int(duration % 60)
            time_str = f"{mins}:{secs:02d}"

            sub_text = f"{artist} • {album} • {time_str}"
            sub_lbl = ctk.CTkLabel(info_frame, text=sub_text, font=("Arial", 11), text_color="gray", anchor="w")
            sub_lbl.pack(fill="x")
            
            qual_lbl = ctk.CTkLabel(
                row_frame,
                text=quality_detail,
                text_color=q_color,
                font=("Arial", 11, "bold"),
                width=150,
                anchor="e",
                justify="right",
                wraplength=150
            )
            qual_lbl.pack(side="right", padx=(5, 10))

            # Download Button
            dl_btn = ctk.CTkButton(row_frame, text="Download", width=80, height=28,
                                   command=lambda: self.on_download(item_id, f"{artist} - {title}", "TRACK"))
            dl_btn.pack(side="right", padx=10, pady=5)

            # Play Button
            play_btn = ctk.CTkButton(row_frame, text="Play", width=60, height=28, fg_color="green",
                                     command=lambda: self.on_play(item_id))
            play_btn.pack(side="right", padx=5)
