import customtkinter as ctk

class SearchResultsView(ctk.CTkScrollableFrame):
    def __init__(self, master, on_play, on_download, **kwargs):
        super().__init__(master, label_text="Results", **kwargs)
        self.on_play = on_play
        self.on_download = on_download

    def clear(self):
        for widget in self.winfo_children():
            widget.destroy()

    def display_message(self, message):
        self.clear()
        ctk.CTkLabel(self, text=message).pack(pady=20)

    def populate(self, items):
        self.clear()
        for item in items:
            self._create_row(item)

    def _create_row(self, item):
        track_id = item.get("id")
        title = item.get("title", "Unknown")
        artist = item.get("artist", {}).get("name", "Unknown Artist")
        album = item.get("album", {}).get("title", "Unknown Album")
        duration = item.get("duration", 0)
        
        # Format duration
        mins = int(duration / 60)
        secs = int(duration % 60)
        time_str = f"{mins}:{secs:02d}"

        # Parse Quality
        quality = item.get("audioQuality", "UNKNOWN")
        tags = item.get("mediaMetadata", {}).get("tags", [])
        
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

        row_frame = ctk.CTkFrame(self)
        row_frame.pack(fill="x", pady=2)
        
        # Info Group
        info_frame = ctk.CTkFrame(row_frame, fg_color="transparent")
        info_frame.pack(side="left", padx=10, pady=5, fill="x", expand=True)
        
        title_lbl = ctk.CTkLabel(info_frame, text=title, font=("Arial", 13, "bold"), anchor="w")
        title_lbl.pack(fill="x")
        
        sub_text = f"{artist} • {album} • {time_str}"
        sub_lbl = ctk.CTkLabel(info_frame, text=sub_text, font=("Arial", 11), text_color="gray", anchor="w")
        sub_lbl.pack(fill="x")
        
        # Quality Label
        q_color = "gray"
        if "Hi-Res" in display_quality or "Master" in display_quality:
            q_color = "#FFA500" # Gold/Orange
        elif "Lossless" in display_quality:
            q_color = "#00BFFF" # Blue
            
        qual_lbl = ctk.CTkLabel(row_frame, text=display_quality, text_color=q_color, font=("Arial", 11, "bold"), width=100, anchor="e")
        qual_lbl.pack(side="right", padx=(5, 10))

        # Download Button
        dl_btn = ctk.CTkButton(row_frame, text="Download", width=80, height=28,
                               command=lambda: self.on_download(track_id, f"{artist} - {title}"))
        dl_btn.pack(side="right", padx=10, pady=5)

        # Play Button
        play_btn = ctk.CTkButton(row_frame, text="Play", width=60, height=28, fg_color="green",
                                 command=lambda: self.on_play(track_id))
        play_btn.pack(side="right", padx=5)
