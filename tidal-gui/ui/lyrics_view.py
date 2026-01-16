import customtkinter as ctk
import re
import logging
from bisect import bisect_right
from typing import List, Tuple, Optional, Callable

logger = logging.getLogger("kozyfy.lyrics")


class LyricsLine(ctk.CTkLabel):
    """A single lyrics line with animation support."""
    
    def __init__(self, master, text: str, timestamp_ms: int, **kwargs):
        super().__init__(master, **kwargs)
        self.text = text
        self.timestamp_ms = timestamp_ms
        self.is_active = False
        
        self.configure(
            text=text,
            font=("Arial", 14),
            text_color="#888888",
            anchor="center",
            wraplength=450
        )
    
    def set_active(self, active: bool):
        """Animate the line when it becomes active."""
        if active and not self.is_active:
            self.is_active = True
            self.configure(
                font=("Arial", 18, "bold"),
                text_color="#1DB954"  # Spotify-like green for active line
            )
        elif not active and self.is_active:
            self.is_active = False
            self.configure(
                font=("Arial", 14),
                text_color="#888888"
            )
    
    def set_upcoming(self):
        """Style for upcoming lines."""
        if not self.is_active:
            self.configure(text_color="#AAAAAA")
    
    def set_passed(self):
        """Style for lines that have passed."""
        if not self.is_active:
            self.configure(text_color="#666666")


class LyricsWindow(ctk.CTkToplevel):
    """Window displaying synchronized lyrics with animations."""
    
    def __init__(self, master, get_progress_callback: Callable, **kwargs):
        super().__init__(master, **kwargs)
        
        self.title("Lyrics")
        self.geometry("500x700")
        self.configure(fg_color="#121212")
        
        # Callbacks
        self.get_progress = get_progress_callback
        
        # Lyrics data
        self.lyrics_lines: List[LyricsLine] = []
        self.synced_lyrics: List[Tuple[int, str]] = []  # (timestamp_ms, text)
        self.current_line_index = -1
        self.is_synced = False
        self.track_info = None
        self.spacer_widgets = []  # Track spacers for cleanup
        
        # Auto-scroll state
        self.auto_scroll = True
        self.user_scrolling = False
        self._timestamp_index: List[int] = []
        self._last_progress_ms = -1
        self._user_scroll_reset_job = None
        self._update_interval_ms = 200
        
        self._create_ui()
        self._start_updater()
        
        # Bind close event
        self.protocol("WM_DELETE_WINDOW", self.hide_window)
        
        # Start hidden
        self.withdraw()
    
    def _create_ui(self):
        """Create the lyrics window UI."""
        # Header with track info
        self.header_frame = ctk.CTkFrame(self, fg_color="#1a1a1a", height=80)
        self.header_frame.pack(fill="x", padx=10, pady=10)
        self.header_frame.pack_propagate(False)

        self.header_content = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        self.header_content.place(relx=0.5, rely=0.5, anchor="center")

        self.cover_label = ctk.CTkLabel(
            self.header_content,
            text="No Art",
            width=60,
            height=60,
            fg_color="#2a2a2a",
            corner_radius=6
        )
        self.cover_label.pack(side="left", padx=(0, 10))

        self.header_text = ctk.CTkFrame(self.header_content, fg_color="transparent")
        self.header_text.pack(side="left", fill="both", expand=True)
        
        self.title_label = ctk.CTkLabel(
            self.header_text,
            text="No Track Playing",
            font=("Arial", 16, "bold"),
            text_color="white",
            anchor="w"
        )
        self.title_label.pack(anchor="w")
        
        self.artist_label = ctk.CTkLabel(
            self.header_text,
            text="",
            font=("Arial", 12),
            text_color="#888888",
            anchor="w"
        )
        self.artist_label.pack(anchor="w")
        
        # Scrollable lyrics container
        self.lyrics_container = ctk.CTkScrollableFrame(
            self,
            fg_color="#121212",
            scrollbar_button_color="#333333",
            scrollbar_button_hover_color="#444444"
        )
        self.lyrics_container.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # Bind scroll events to detect user scrolling
        self.lyrics_container.bind("<MouseWheel>", self._on_user_scroll)
        self.lyrics_container.bind("<Button-4>", self._on_user_scroll)
        self.lyrics_container.bind("<Button-5>", self._on_user_scroll)
        
        # Status label for no lyrics
        self.status_label = ctk.CTkLabel(
            self.lyrics_container,
            text="",
            font=("Arial", 14),
            text_color="#666666"
        )
        
        # Bottom controls
        self.controls_frame = ctk.CTkFrame(self, fg_color="#1a1a1a", height=50)
        self.controls_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        self.auto_scroll_var = ctk.BooleanVar(value=True)
        self.auto_scroll_switch = ctk.CTkSwitch(
            self.controls_frame,
            text="Auto-scroll",
            variable=self.auto_scroll_var,
            command=self._toggle_auto_scroll,
            font=("Arial", 11)
        )
        self.auto_scroll_switch.pack(side="left", padx=20, pady=10)
        
        self.sync_status = ctk.CTkLabel(
            self.controls_frame,
            text="",
            font=("Arial", 11),
            text_color="#666666"
        )
        self.sync_status.pack(side="right", padx=20, pady=10)
    
    def _on_user_scroll(self, event):
        """Handle user scroll events."""
        if self.auto_scroll_var.get():
            self.user_scrolling = True
            # Reset after 3 seconds of no scrolling
            if self._user_scroll_reset_job is not None:
                self.after_cancel(self._user_scroll_reset_job)
            self._user_scroll_reset_job = self.after(3000, self._reset_user_scroll)
    
    def _reset_user_scroll(self):
        """Reset user scrolling flag."""
        self.user_scrolling = False
        self._user_scroll_reset_job = None
    
    def _toggle_auto_scroll(self):
        """Toggle auto-scroll feature."""
        self.auto_scroll = self.auto_scroll_var.get()
        self.user_scrolling = False
    
    def show_window(self):
        """Show the lyrics window."""
        self.deiconify()
        self.lift()
        self.focus()
    
    def hide_window(self):
        """Hide the lyrics window."""
        self.withdraw()
    
    def toggle_window(self):
        """Toggle visibility of the lyrics window."""
        if self.winfo_viewable():
            self.hide_window()
        else:
            self.show_window()
    
    def set_track_info(self, track_info: dict, cover_image=None):
        """Update track info in header."""
        self.track_info = track_info
        self.title_label.configure(text=track_info.get("title", "Unknown"))
        self.artist_label.configure(text=track_info.get("artist", ""))
        if cover_image:
            self.cover_label.configure(image=cover_image, text="")
            self.cover_label.image = cover_image
        else:
            self.cover_label.configure(image=None, text="No Art")
    
    def load_lyrics(self, lyrics_data: dict):
        """Load and parse lyrics data."""
        # Clear existing lyrics
        self._clear_lyrics()
        
        if not lyrics_data or "error" in lyrics_data:
            self._show_no_lyrics(lyrics_data.get("error", "Lyrics not available"))
            return
        
        # Check for synced subtitles (LRC format)
        subtitles = lyrics_data.get("subtitles")
        plain_lyrics = lyrics_data.get("lyrics")
        
        if subtitles:
            self._parse_synced_lyrics(subtitles)
            self.is_synced = True
            self.sync_status.configure(text="⏱ Synced", text_color="#1DB954")
        elif plain_lyrics:
            self._display_plain_lyrics(plain_lyrics)
            self.is_synced = False
            self.sync_status.configure(text="📝 Plain text", text_color="#888888")
        else:
            self._show_no_lyrics("Lyrics not available")
    
    def _clear_lyrics(self):
        """Clear all lyrics from the container."""
        for line in self.lyrics_lines:
            line.destroy()
        for spacer in self.spacer_widgets:
            try:
                spacer.destroy()
            except:
                pass
        self.lyrics_lines.clear()
        self.synced_lyrics.clear()
        self._timestamp_index.clear()
        self.spacer_widgets.clear()
        self.current_line_index = -1
        self._last_progress_ms = -1
        self.status_label.pack_forget()
        
        # Reset scroll position to top
        try:
            canvas = self.lyrics_container._parent_canvas
            canvas.yview_moveto(0)
        except:
            pass
    
    def _show_no_lyrics(self, message: str = "Lyrics not available"):
        """Display no lyrics message."""
        self._clear_lyrics()
        self.status_label.configure(text=message)
        self.status_label.pack(pady=50)
        self.sync_status.configure(text="", text_color="#666666")
        self.is_synced = False
    
    def _parse_synced_lyrics(self, subtitles: str):
        """Parse LRC format lyrics with timestamps."""
        # LRC format: [mm:ss.xx]lyrics text
        # Also handle: [mm:ss:xx] and [mm:ss]
        pattern = r'\[(\d{2}):(\d{2})[:.](\d{2,3})?\](.*)$'
        
        lines = subtitles.strip().split('\n')
        parsed_lines = []
        
        for line in lines:
            match = re.match(pattern, line.strip())
            if match:
                minutes = int(match.group(1))
                seconds = int(match.group(2))
                ms_part = match.group(3)
                
                if ms_part:
                    # Handle both centiseconds (xx) and milliseconds (xxx)
                    if len(ms_part) == 2:
                        milliseconds = int(ms_part) * 10
                    else:
                        milliseconds = int(ms_part)
                else:
                    milliseconds = 0
                
                timestamp_ms = (minutes * 60 + seconds) * 1000 + milliseconds
                text = match.group(4).strip()
                
                if text:  # Skip empty lines but keep timestamp
                    parsed_lines.append((timestamp_ms, text))
            elif line.strip() and not line.strip().startswith('['):
                # Plain text line without timestamp
                parsed_lines.append((0, line.strip()))
        
        # Sort by timestamp
        parsed_lines.sort(key=lambda x: x[0])
        self.synced_lyrics = parsed_lines
        self._timestamp_index = [timestamp_ms for timestamp_ms, _ in self.synced_lyrics]
        
        # Create UI elements
        self._create_lyrics_ui()
    
    def _display_plain_lyrics(self, lyrics: str):
        """Display plain text lyrics without sync."""
        lines = lyrics.strip().split('\n')
        
        for line in lines:
            text = line.strip()
            if text:
                self.synced_lyrics.append((0, text))
        self._timestamp_index = [timestamp_ms for timestamp_ms, _ in self.synced_lyrics]
        
        self._create_lyrics_ui()
    
    def _create_lyrics_ui(self):
        """Create UI elements for lyrics lines."""
        # Add smaller spacer at top (just enough for centering first line when active)
        spacer_top = ctk.CTkFrame(self.lyrics_container, fg_color="transparent", height=50)
        spacer_top.pack(fill="x")
        spacer_top.pack_propagate(False)
        self.spacer_widgets.append(spacer_top)
        
        for timestamp_ms, text in self.synced_lyrics:
            line_widget = LyricsLine(
                self.lyrics_container,
                text=text,
                timestamp_ms=timestamp_ms
            )
            line_widget.pack(pady=8, padx=20, fill="x")
            self.lyrics_lines.append(line_widget)
        
        # Add spacer at bottom for scrolling past last line
        spacer_bottom = ctk.CTkFrame(self.lyrics_container, fg_color="transparent", height=200)
        spacer_bottom.pack(fill="x")
        spacer_bottom.pack_propagate(False)
        self.spacer_widgets.append(spacer_bottom)
        
        # Force layout update and scroll to top
        self.lyrics_container.update_idletasks()
        
        # Reset scroll to top so lyrics are visible from the start
        try:
            canvas = self.lyrics_container._parent_canvas
            canvas.yview_moveto(0)
        except:
            pass
    
    def _start_updater(self):
        """Start the lyrics sync updater."""
        delay_ms = self._update_interval_ms
        if self.is_synced and self.lyrics_lines and self.winfo_viewable():
            delay_ms = self._update_active_line() or self._update_interval_ms
        
        # Schedule next update
        self.after(delay_ms, self._start_updater)

    def _get_next_update_delay(self, current_ms: int, next_index: int) -> int:
        """Compute adaptive update interval based on next lyric timestamp."""
        if next_index < 0 or next_index >= len(self._timestamp_index):
            return self._update_interval_ms

        delta_ms = self._timestamp_index[next_index] - current_ms
        if delta_ms <= 0:
            return 50
        if delta_ms <= 200:
            return 50
        if delta_ms <= 800:
            return 100
        if delta_ms <= 2000:
            return 200
        return 300
    
    def _update_active_line(self):
        """Update which lyrics line is active based on playback position."""
        if not self.synced_lyrics:
            return self._update_interval_ms
        
        try:
            current_ms, length_ms, progress = self.get_progress()
            
            if length_ms <= 0:
                return self._update_interval_ms
            
            if not self._timestamp_index:
                return self._update_interval_ms
            
            progress_changed = current_ms != self._last_progress_ms
            if progress_changed:
                self._last_progress_ms = current_ms
                new_index = bisect_right(self._timestamp_index, current_ms) - 1
            else:
                new_index = self.current_line_index
            
            # Update line styles if index changed
            if new_index != self.current_line_index:
                # Reset previous active line
                if 0 <= self.current_line_index < len(self.lyrics_lines):
                    self.lyrics_lines[self.current_line_index].set_active(False)
                    self.lyrics_lines[self.current_line_index].set_passed()
                
                # Set new active line
                if 0 <= new_index < len(self.lyrics_lines):
                    self.lyrics_lines[new_index].set_active(True)
                    
                    # Auto-scroll to active line
                    if self.auto_scroll and not self.user_scrolling:
                        self._scroll_to_line(new_index)
                
                # Update upcoming lines style
                for i in range(new_index + 1, min(new_index + 4, len(self.lyrics_lines))):
                    if i < len(self.lyrics_lines):
                        self.lyrics_lines[i].set_upcoming()
                
                self.current_line_index = new_index
            
            return self._get_next_update_delay(current_ms, new_index + 1)
                
        except Exception:
            logger.exception("Lyrics update error")

        return self._update_interval_ms
    
    def _scroll_to_line(self, index: int):
        """Scroll the lyrics container to center the given line."""
        if not self.lyrics_lines or index < 0 or index >= len(self.lyrics_lines):
            return
        
        try:
            # Get the target line widget
            line_widget = self.lyrics_lines[index]
            
            # Force geometry calculations
            self.lyrics_container.update_idletasks()
            
            # Access the underlying canvas of CTkScrollableFrame
            canvas = self.lyrics_container._parent_canvas
            
            # Get the line's position - we need to get it relative to the scrollable content
            # In CTkScrollableFrame, widgets are packed into an inner frame
            # winfo_y() gives position relative to the immediate parent (the inner frame)
            line_y = line_widget.winfo_y()
            line_height = line_widget.winfo_height()
            
            # Get visible area height
            visible_height = canvas.winfo_height()
            
            # Get the scroll region to know total content height
            canvas.update_idletasks()
            
            # Try to get scrollregion, or calculate from bbox
            try:
                sr = canvas.cget('scrollregion')
                if sr:
                    parts = str(sr).split()
                    total_height = float(parts[3]) if len(parts) >= 4 else 0
                else:
                    total_height = 0
            except:
                total_height = 0
            
            if total_height == 0:
                bbox = canvas.bbox("all")
                if bbox:
                    total_height = bbox[3]
                else:
                    return
            
            if total_height <= visible_height:
                return  # No scrolling needed, all content visible
            
            # Calculate where the line center should be
            line_center = line_y + (line_height / 2)
            
            # We want line_center to appear at visible_height / 2 from top
            # So we need to scroll so that: scroll_top + visible_height/2 = line_center
            # Therefore: scroll_top = line_center - visible_height/2
            desired_scroll_top = line_center - (visible_height / 2)
            
            # Clamp to valid scroll range
            max_scroll = total_height - visible_height
            desired_scroll_top = max(0, min(max_scroll, desired_scroll_top))
            
            # Convert to yview fraction (0 to 1 range representing top position)
            if total_height > 0:
                fraction = desired_scroll_top / total_height
                canvas.yview_moveto(fraction)
            
        except Exception:
            logger.exception("Lyrics scroll error")
    
    def reset(self):
        """Reset lyrics state."""
        self._clear_lyrics()
        self.title_label.configure(text="No Track Playing")
        self.artist_label.configure(text="")
        self.cover_label.configure(image=None, text="No Art")
        self.sync_status.configure(text="")
        self.track_info = None
