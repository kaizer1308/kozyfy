import customtkinter as ctk
from .theme import COLORS, FONTS, RADII

class SearchResultsView(ctk.CTkScrollableFrame):
    def __init__(self, master, on_play, on_download, **kwargs):
        super().__init__(
            master,
            label_text="Results",
            label_font=FONTS["section"],
            label_text_color=COLORS["text"],
            label_fg_color=COLORS["panel"],
            **kwargs,
        )
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
        ctk.CTkLabel(
            self,
            text=message,
            text_color=COLORS["text_muted"],
            font=FONTS["body"],
        ).pack(pady=20)

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
        q_color = COLORS["text_muted"]
        if "Hi-Res" in display_quality or "Master" in display_quality:
            q_color = COLORS["warning"]
        elif "Lossless" in display_quality:
            q_color = COLORS["accent_alt"]

        row_frame = ctk.CTkFrame(
            self,
            fg_color=COLORS["panel_alt"],
            corner_radius=RADII["button"],
            border_width=1,
            border_color=COLORS["border"],
        )
        row_frame.pack(fill="x", pady=6, padx=6)
        
        # Info Group
        info_frame = ctk.CTkFrame(row_frame, fg_color="transparent")
        info_frame.pack(side="left", padx=12, pady=10, fill="x", expand=True)
        
        title_lbl = ctk.CTkLabel(
            info_frame,
            text=title,
            font=FONTS["subtitle"],
            text_color=COLORS["text"],
            anchor="w",
        )
        title_lbl.pack(fill="x")
        
        if item_type == "ALBUM":
            release_date = item.get("releaseDate", "")
            tracks_count = item.get("numberOfTracks", 0)
            sub_text = f"Album • {artist} • {tracks_count} Tracks • {release_date}"
            
            sub_lbl = ctk.CTkLabel(
                info_frame,
                text=sub_text,
                font=FONTS["body"],
                text_color=COLORS["text_muted"],
                anchor="w",
            )
            sub_lbl.pack(fill="x")
            
            qual_lbl = ctk.CTkLabel(
                row_frame,
                text=quality_detail,
                text_color=q_color,
                font=FONTS["small_bold"],
                width=150,
                anchor="e",
                justify="right",
                wraplength=150
            )
            qual_lbl.pack(side="right", padx=(5, 10))

            # Download Button (Album)
            dl_btn = ctk.CTkButton(
                row_frame,
                text="Download",
                width=90,
                height=30,
                fg_color=COLORS["panel_highlight"],
                hover_color=COLORS["border"],
                text_color=COLORS["text"],
                corner_radius=RADII["button"],
                font=FONTS["small_bold"],
                command=lambda: self.on_download(item_id, f"{artist} - {title}", "ALBUM"),
            )
            dl_btn.pack(side="right", padx=12, pady=10)
            
        else: # TRACK
            album = item.get("album", {}).get("title", "Unknown Album")
            duration = item.get("duration", 0)
            
            # Format duration
            mins = int(duration / 60)
            secs = int(duration % 60)
            time_str = f"{mins}:{secs:02d}"

            sub_text = f"{artist} • {album} • {time_str}"
            sub_lbl = ctk.CTkLabel(
                info_frame,
                text=sub_text,
                font=FONTS["body"],
                text_color=COLORS["text_muted"],
                anchor="w",
            )
            sub_lbl.pack(fill="x")
            
            qual_lbl = ctk.CTkLabel(
                row_frame,
                text=quality_detail,
                text_color=q_color,
                font=FONTS["small_bold"],
                width=150,
                anchor="e",
                justify="right",
                wraplength=150
            )
            qual_lbl.pack(side="right", padx=(5, 10))

            # Download Button
            dl_btn = ctk.CTkButton(
                row_frame,
                text="Download",
                width=90,
                height=30,
                fg_color=COLORS["panel_highlight"],
                hover_color=COLORS["border"],
                text_color=COLORS["text"],
                corner_radius=RADII["button"],
                font=FONTS["small_bold"],
                command=lambda: self.on_download(item_id, f"{artist} - {title}", "TRACK"),
            )
            dl_btn.pack(side="right", padx=12, pady=10)

            # Play Button
            play_btn = ctk.CTkButton(
                row_frame,
                text="Play",
                width=70,
                height=30,
                fg_color=COLORS["accent"],
                hover_color=COLORS["accent_alt"],
                text_color=COLORS["bg"],
                corner_radius=RADII["button"],
                font=FONTS["small_bold"],
                command=lambda: self.on_play(item_id),
            )
            play_btn.pack(side="right", padx=6, pady=10)
