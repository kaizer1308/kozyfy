import sys
import os

# Fix for bundled app - ensure proper import paths
if getattr(sys, 'frozen', False):
    # Running as compiled exe
    os.chdir(os.path.dirname(sys.executable))
    # Add the exe directory to path for imports
    sys.path.insert(0, os.path.dirname(sys.executable))

import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
import glob
import requests
import base64
import certifi
from PIL import Image
from io import BytesIO

# Set SSL certificate path for bundled app
os.environ['SSL_CERT_FILE'] = certifi.where()
os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()

from api_handler import TidalApiHandler
from logic.playback import PlaybackManager
from ui.player_bar import PlayerBar
from ui.search_view import SearchResultsView
from ui.downloads_view import DownloadsWindow
from ui.lyrics_view import LyricsWindow
from utils.paths import get_temp_dir, get_default_download_dir, get_config_dir
from utils.dependencies import check_all_dependencies, get_missing_dependencies_message

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class TidalApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Kozyfy")
        self.geometry("1000x800")
        
        # Check dependencies before proceeding
        self._check_dependencies()
        
        self.api = TidalApiHandler()
        self.api.set_base_url("https://triton.squid.wtf")
        
        # Use proper default download path instead of cwd
        self.download_path = self._load_download_path()
        
        # Store temp directory for temp files
        self.temp_dir = get_temp_dir()

        self.playback = PlaybackManager()
        
        self.downloads_window = DownloadsWindow(self)
        
        # Create lyrics window with playback progress callback
        self.lyrics_window = LyricsWindow(self, self.playback.get_progress)
        
        # State
        self.current_results = []
        
        self._setup_layout()
        
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def _check_dependencies(self):
        """Check for required dependencies and show warning if missing."""
        # Check FFmpeg first (doesn't cause DLL errors)
        deps = check_all_dependencies()
        
        # FFmpeg is critical for downloads
        if not deps["ffmpeg"]["ok"]:
            self.after(100, lambda: messagebox.showwarning(
                "FFmpeg Not Found",
                "FFmpeg is not installed or not in PATH.\n\n"
                "Download features will not work.\n\n"
                "Please install FFmpeg from:\n"
                "https://ffmpeg.org/download.html\n\n"
                "Make sure to add FFmpeg to your system PATH."
            ))
        
        # VLC check is now done lazily when playback is attempted
        # to avoid DLL errors on startup
    
    def _load_download_path(self):
        """Load saved download path or use default."""
        config_file = os.path.join(get_config_dir(), "settings.txt")
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.startswith("download_path="):
                            path = line.strip().split("=", 1)[1]
                            if os.path.exists(path):
                                return path
        except:
            pass
        return get_default_download_dir()
    
    def _save_download_path(self):
        """Save download path to config."""
        config_file = os.path.join(get_config_dir(), "settings.txt")
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                f.write(f"download_path={self.download_path}\n")
        except:
            pass

    def _setup_layout(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0) # Top
        self.grid_rowconfigure(1, weight=0) # Search
        self.grid_rowconfigure(2, weight=1) # Results
        self.grid_rowconfigure(3, weight=0) # Player Bar

        self._create_top_bar()
        self._create_search_bar()
        self._create_results_area()
        self._create_player_bar()

    def _create_top_bar(self):
        self.top_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.top_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        # Settings Button (Left)
        ctk.CTkButton(self.top_frame, text="Settings", width=100, command=self.open_settings).pack(side="left", padx=5)

        # Downloads Button (Left)
        ctk.CTkButton(self.top_frame, text="Downloads", width=100, command=self.downloads_window.show_window).pack(side="left", padx=5)

        # Filter Switch (Rightmost)
        self.filter_var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(self.top_frame, text="Filter Results", variable=self.filter_var, command=self.render_results).pack(side="right", padx=5)

        # Quality Selection (Next to switch)
        self.quality_var = ctk.StringVar(value="HI_RES_LOSSLESS")
        ctk.CTkComboBox(self.top_frame, 
                        values=["HI_RES_LOSSLESS", "LOSSLESS", "HIGH", "LOW"],
                        variable=self.quality_var,
                        width=150,
                        command=self.render_results).pack(side="right", padx=10)

    def _create_search_bar(self):
        self.search_frame = ctk.CTkFrame(self)
        self.search_frame.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="ew")

        # Search Type Selector
        self.search_type_var = ctk.StringVar(value="Tracks")
        self.search_type_combo = ctk.CTkComboBox(self.search_frame, 
                                                 values=["Tracks", "Albums"],
                                                 variable=self.search_type_var,
                                                 width=100)
        self.search_type_combo.pack(side="left", padx=(10, 0), pady=10)

        self.search_entry = ctk.CTkEntry(self.search_frame, placeholder_text="Enter artist, title or album...")
        self.search_entry.pack(side="left", fill="x", expand=True, padx=10, pady=10)
        self.search_entry.bind("<Return>", lambda event: self.start_search())

        self.search_btn = ctk.CTkButton(self.search_frame, text="Search", command=self.start_search)
        self.search_btn.pack(side="right", padx=10)

    def _create_results_area(self):
        self.results_view = SearchResultsView(self, on_play=self.start_playback, on_download=self.start_download)
        self.results_view.grid(row=2, column=0, padx=10, pady=5, sticky="nsew")

    def _create_player_bar(self):
        self.player_bar = PlayerBar(
            self, 
            self.playback, 
            on_download_click=self.on_player_download,
            on_lyrics_click=self.toggle_lyrics_window
        )
        self.player_bar.grid(row=3, column=0, padx=10, pady=10, sticky="ew")

    def toggle_lyrics_window(self):
        """Toggle the lyrics window visibility."""
        self.lyrics_window.toggle_window()

    # --- Actions ---

    def start_search(self):
        query = self.search_entry.get()
        if not query: return
        
        self.search_btn.configure(state="disabled")
        self.results_view.display_message(f"Searching for '{query}'...")
        threading.Thread(target=self.run_search, args=(query,)).start()

    def run_search(self, query):
        search_type = self.search_type_var.get()
        if search_type == "Albums":
            results = self.api.search_albums(query)
            if isinstance(results, list):
                for r in results: r['_type'] = 'ALBUM'
        else:
            results = self.api.search_tracks(query)
            if isinstance(results, list):
                for r in results: r['_type'] = 'TRACK'
                
        self.after(0, lambda: self.handle_search_results(results))

    def handle_search_results(self, results):
        self.search_btn.configure(state="normal")
        if isinstance(results, dict) and "error" in results:
            self.results_view.display_message(f"Error: {results['error']}")
            return
        
        self.current_results = results or []
        self.render_results()

    def render_results(self, _=None):
        if not self.current_results:
            self.results_view.display_message("No results found.")
            return

        items_to_show = []
        target_q = self.quality_var.get()
        filter_on = self.filter_var.get()
        
        expected_q = "HI_RES" if target_q == "HI_RES_LOSSLESS" else target_q
        
        for item in self.current_results:
            if filter_on:
                iq = item.get("audioQuality")
                tags = item.get("mediaMetadata", {}).get("tags", [])
                match = (iq == expected_q)
                if target_q == "HI_RES_LOSSLESS" and ("HIRES_LOSSLESS" in tags or "MQA" in tags or iq == "HI_RES"):
                    match = True
                if not match: continue
            items_to_show.append(item)
            
        self.results_view.populate(items_to_show)
        if not items_to_show and filter_on:
            self.results_view.display_message(f"No items match quality: {target_q}")

    # --- Playback Logic (Controller) ---

    def start_playback(self, track_id):
        # Resume if same track handled by PlayerBar/Manager
        if self.playback.current_playing_id == track_id:
            self.player_bar.toggle_play()
            return
        
        target_quality = self.quality_var.get()
        threading.Thread(target=self._playback_worker, args=(track_id, target_quality)).start()

    def _playback_worker(self, track_id, quality):
        # 1. Fetch Metadata
        details = self.api.get_track_details(track_id)
        track_info = {
            "title": details.get("title", "Unknown"),
            "artist": details.get("artist", {}).get("name", "Unknown"),
            "album": details.get("album", {}).get("title", ""),
            "cover": details.get("album", {}).get("cover"),
            "id": track_id
        }
        
        # 2. Fetch Cover
        cover_img = self._fetch_cover_image(track_info["cover"])
        
        # 3. Fetch Stream
        stream_data = self.api.get_stream_url(track_id, quality=quality)
        quality_detail = self._build_audio_metadata(details, stream_data)
        if quality_detail:
            track_info["quality_detail"] = quality_detail
        final_url = self._resolve_stream_url(stream_data, track_id, is_playback=True)
        
        if final_url:
            self.after(0, lambda: self._start_vlc(final_url, track_info, cover_img))
        else:
            print("[App] Failed to resolve stream for playback")
            self.after(0, lambda: messagebox.showerror("Playback Error", "Failed to get stream URL for this track."))

    def _start_vlc(self, url, track_info, cover_img):
        # Check VLC availability before attempting playback
        if not self.playback.is_vlc_available():
            error_msg = self.playback.get_vlc_error() or "VLC is not available"
            messagebox.showerror(
                "Playback Error",
                f"{error_msg}\n\n"
                "Please install/update VLC Media Player (64-bit):\n"
                "https://www.videolan.org/vlc/\n\n"
                "After installing, restart Kozyfy."
            )
            return
        
        if self.playback.play(url, track_info):
            self.player_bar.update_track_info(track_info, cover_img)
            self.current_cover_ref = cover_img # Prevent GC
            
            # Fetch and load lyrics for the new track
            self._load_lyrics_for_track(track_info, cover_img)
        else:
            messagebox.showerror("Playback Error", "Failed to start playback. Please check VLC installation.")

    def _load_lyrics_for_track(self, track_info, cover_img=None):
        """Fetch and load lyrics for the current track."""
        # Update lyrics window with track info immediately
        self.lyrics_window.set_track_info(track_info, cover_img)
        
        # Fetch lyrics in background thread
        threading.Thread(
            target=self._fetch_lyrics_worker, 
            args=(track_info["id"],),
            daemon=True
        ).start()
    
    def _fetch_lyrics_worker(self, track_id):
        """Worker thread to fetch lyrics from API."""
        print(f"[App] Fetching lyrics for track {track_id}...")
        lyrics_data = self.api.get_lyrics(track_id)
        
        # Load lyrics in main thread
        self.after(0, lambda: self.lyrics_window.load_lyrics(lyrics_data))

    # --- Download Logic (Controller) ---
    def start_download(self, item_id, item_title, item_type="TRACK"):
        if item_type == "ALBUM":
             threading.Thread(target=self._download_album_worker, args=(item_id, item_title)).start()
             return

        if item_id in self.downloads_window.active_downloads:
            print(f"[App] Skipping download: {item_title} (Already in queue)")
            return

        quality = self.quality_var.get()
        threading.Thread(target=self._download_worker, args=(item_id, item_title, quality)).start()

    def _download_album_worker(self, album_id, album_title):
        print(f"[App] Fetching album {album_id}...")
        try:
            album_data = self.api.get_album(album_id)
            items = album_data.get("items", [])
            
            if not items:
                print("[App] Album empty or failed to load items.")
                return

            # Create folder
            safe_album = "".join([c for c in album_title if c.isalpha() or c.isdigit() or c in " .-_()"]).strip()
            album_dir = os.path.join(self.download_path, safe_album)
            if not os.path.exists(album_dir):
                os.makedirs(album_dir)
                
            print(f"[App] Starting album download: {album_title} ({len(items)} tracks)")
            
            quality = self.quality_var.get()
            for item_obj in items:
                # Handle wrapped items
                item = item_obj.get("item", item_obj)
                
                t_id = item.get("id")
                title = item.get("title")
                artist = item.get("artist", {}).get("name")
                
                if not artist and "artists" in item:
                     artist = ", ".join([a.get("name", "") for a in item["artists"]])
                     
                display = f"{artist} - {title}"
                
                if t_id and t_id not in self.downloads_window.active_downloads:
                    # Download in parallel
                    threading.Thread(target=self._download_worker, args=(t_id, display, quality, album_dir)).start()
        except Exception as e:
            print(f"Album Queue Error: {e}")

    def on_player_download(self, track_info):
        name = f"{track_info['artist']} - {track_info['title']}"
        self.start_download(track_info['id'], name)

    def _download_worker(self, track_id, filename, quality, output_dir=None):
        print(f"[App] Downloading {filename}...")
        target_dir = output_dir if output_dir else self.download_path
        
        # Add to Download UI
        self.after(0, lambda: self.downloads_window.add_download(track_id, filename))
        
        details = self.api.get_track_details(track_id)
        duration = details.get("duration", 0)
        
        metadata = {
            "title": details.get("title", filename.split(" - ")[-1]),
            "artist": details.get("artist", {}).get("name", ""),
            "album": details.get("album", {}).get("title", ""),
            "date": str(details.get("streamStartDate", ""))[:4],
            "track": f"{details.get('trackNumber', '')}",
            "disc": f"{details.get('volumeNumber', '')}",
            "copyright": details.get("copyright", ""),
            "comment": "Kozydot<3You"
        }
        
        # Cover for file tagging - save to temp dir to avoid permission issues
        cover_path = None
        if details.get("album", {}).get("cover"):
            try:
                uuid = details["album"]["cover"].replace('-', '/')
                curr_url = f"https://resources.tidal.com/images/{uuid}/1280x1280.jpg"
                r = requests.get(curr_url, timeout=15)
                if r.status_code == 200:
                    cover_path = os.path.join(self.temp_dir, f"cover_{track_id}.jpg")
                    with open(cover_path, "wb") as f: f.write(r.content)
            except Exception as e:
                print(f"[App] Cover download failed: {e}")

        stream_data = self.api.get_stream_url(track_id, quality=quality)
        final_url = self._resolve_stream_url(stream_data, track_id, is_playback=False)
        
        if not final_url:
            print("[App] Download failed: No URL")
            self.after(0, lambda: self.downloads_window.finish_download(track_id, False, "No URL"))
            if cover_path and os.path.exists(cover_path): os.remove(cover_path)
            return
            
        safe_name = "".join([c for c in filename if c.isalpha() or c.isdigit() or c in " .-_()"]).strip()
        ext = ".flac" if quality in ["HI_RES_LOSSLESS", "LOSSLESS"] else ".m4a"
        output_path = os.path.join(target_dir, f"{safe_name}{ext}")
        
        def progress_cb(p):
            self.after(0, lambda: self.downloads_window.update_download(track_id, p))
        
        success, msg = self.api.download_stream(final_url, output_path, metadata, cover_path, progress_cb, duration=duration)
        
        print(f"[App] Download {'Complete' if success else 'Failed'}: {output_path}")
        self.after(0, lambda: self.downloads_window.finish_download(track_id, success, msg))

        # Cleanup
        if cover_path and os.path.exists(cover_path): os.remove(cover_path)

    # --- Helpers ---
    def _fetch_cover_image(self, uuid):
        if not uuid: return None
        try:
            clean_uuid = uuid.replace('-', '/')
            url = f"https://resources.tidal.com/images/{clean_uuid}/320x320.jpg"
            r = requests.get(url)
            if r.status_code == 200:
                pil_img = Image.open(BytesIO(r.content))
                return ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(60, 60))
        except Exception as e:
            print(f"Cover Load Error: {e}")
        return None

    def _format_quality_label(self, audio_quality, tags):
        if not audio_quality:
            audio_quality = ""
        if "HIRES_LOSSLESS" in tags or audio_quality == "HI_RES_LOSSLESS":
            return "Hi-Res Lossless"
        if audio_quality == "LOSSLESS":
            return "Lossless"
        if audio_quality == "HI_RES":
            return "Hi-Res"
        if audio_quality == "HIGH":
            return "High"
        if audio_quality == "LOW":
            return "Low"
        return audio_quality.replace("_", " ").title() if audio_quality else ""

    def _build_audio_metadata(self, details, stream_data):
        if not isinstance(details, dict) or not isinstance(stream_data, dict):
            return ""

        if "data" in stream_data and isinstance(stream_data["data"], dict):
            stream_data = stream_data["data"]

        tags = details.get("mediaMetadata", {}).get("tags", []) or []
        audio_quality = stream_data.get("audioQuality") or details.get("audioQuality")
        display_quality = self._format_quality_label(audio_quality, tags)

        bit_depth = stream_data.get("bitDepth")
        sample_rate = stream_data.get("sampleRate")
        sample_rate_label = ""
        if sample_rate:
            khz = sample_rate / 1000
            if abs(khz - round(khz)) < 0.01:
                sample_rate_label = f"{int(round(khz))}kHz"
            else:
                sample_rate_label = f"{khz:.1f}kHz"

        audio_mode = stream_data.get("audioMode")
        if not audio_mode:
            audio_modes = details.get("audioModes") or []
            if isinstance(audio_modes, list) and audio_modes:
                audio_mode = "/".join(audio_modes)

        extras = []
        if "MQA" in tags:
            extras.append("MQA")
        if "DOLBY_ATMOS" in tags:
            extras.append("Dolby Atmos")
        if "SONY_360RA" in tags:
            extras.append("360 Reality Audio")

        meta_parts = []
        if display_quality:
            meta_parts.append(display_quality)
        if bit_depth and sample_rate_label:
            meta_parts.append(f"{bit_depth}-bit/{sample_rate_label}")
        elif bit_depth:
            meta_parts.append(f"{bit_depth}-bit")
        elif sample_rate_label:
            meta_parts.append(sample_rate_label)
        if audio_mode:
            meta_parts.append(audio_mode.title())
        if extras:
            meta_parts.extend(extras)

        return " • ".join(meta_parts)

    def _resolve_stream_url(self, stream_data, track_id, is_playback=False):
        if "data" in stream_data and isinstance(stream_data["data"], dict):
            stream_data = stream_data["data"]
        
        final_url = stream_data.get("url")
        manifest_b64 = stream_data.get("manifest")
        mime = stream_data.get("manifestMimeType", "")

        if manifest_b64:
            try:
                decoded = base64.b64decode(manifest_b64).decode('utf-8')
                if "application/vnd.tidal.bts" in mime:
                    import json
                    bts = json.loads(decoded)
                    if "urls" in bts and bts["urls"]:
                        final_url = bts["urls"][0]
                else:
                    ext = ".mpd" if "dash" in mime else ".m3u8"
                    # Save temp manifest file to proper temp directory
                    prefix = "play" if is_playback else "dl"
                    temp_file = os.path.join(self.temp_dir, f"temp_{prefix}_{track_id}{ext}")
                    with open(temp_file, "w", encoding="utf-8") as f:
                        f.write(decoded)
                    final_url = temp_file
            except: return None
            
        return final_url

    def open_settings(self):
        # Simplified for brevity
        win = ctk.CTkToplevel(self)
        win.title("Settings")
        win.geometry("400x250")
        
        # API URL
        ctk.CTkLabel(win, text="API URL:").pack(pady=5)
        ent = ctk.CTkEntry(win, width=300)
        ent.insert(0, self.api.base_url)
        ent.pack(pady=5)

        # Download Path
        ctk.CTkLabel(win, text="Download Location:").pack(pady=5)
        path_frame = ctk.CTkFrame(win, fg_color="transparent")
        path_frame.pack(pady=5, fill="x", padx=20)
        
        path_label = ctk.CTkLabel(path_frame, text=self.download_path, anchor="w")
        path_label.pack(side="left", fill="x", expand=True, padx=5)
        
        def choose_folder():
            d = filedialog.askdirectory(initialdir=self.download_path)
            if d:
                self.download_path = d
                path_label.configure(text=d)
        
        ctk.CTkButton(path_frame, text="...", width=40, command=choose_folder).pack(side="right", padx=5)

        def save():
            self.api.set_base_url(ent.get())
            self._save_download_path()  # Persist download path
            win.destroy()
        
        ctk.CTkButton(win, text="Save", command=save).pack(pady=20)

    def on_closing(self):
        # Stop playback
        if hasattr(self, 'playback'):
            self.playback.stop()

        # Cleanup temp files from proper temp directory
        print("[Cleanup] Cleaning up temporary files...")
        try:
            temp_dir = getattr(self, 'temp_dir', get_temp_dir())
            temp_patterns = [
                os.path.join(temp_dir, "temp_*.mpd"),
                os.path.join(temp_dir, "temp_*.m3u8"),
                os.path.join(temp_dir, "cover_*.jpg"),
            ]
            for pattern in temp_patterns:
                for f in glob.glob(pattern):
                    try:
                        os.remove(f)
                        print(f"[Cleanup] Removed {f}")
                    except Exception as e:
                        print(f"[Cleanup] Failed to remove {f}: {e}")
        except Exception as e:
            print(f"[Cleanup] Error during cleanup: {e}")
                
        self.destroy()
        os._exit(0)

if __name__ == "__main__":
    app = TidalApp()
    app.mainloop()
