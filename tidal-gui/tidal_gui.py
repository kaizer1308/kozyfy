import customtkinter as ctk
from tkinter import filedialog
import threading
import os
import glob
import requests
import base64
from PIL import Image
from io import BytesIO

from api_handler import TidalApiHandler
from logic.playback import PlaybackManager
from ui.player_bar import PlayerBar
from ui.search_view import SearchResultsView
from ui.downloads_view import DownloadsWindow

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class TidalApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Kozyfy")
        self.geometry("1000x800")
        
        self.api = TidalApiHandler()
        self.api.set_base_url("https://triton.squid.wtf")
        
        self.download_path = os.getcwd()

        self.playback = PlaybackManager()
        
        self.downloads_window = DownloadsWindow(self)
        
        # State
        self.current_results = []
        
        self._setup_layout()
        
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

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
        self.player_bar = PlayerBar(self, self.playback, on_download_click=self.on_player_download)
        self.player_bar.grid(row=3, column=0, padx=10, pady=10, sticky="ew")

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
        final_url = self._resolve_stream_url(stream_data, track_id, is_playback=True)
        
        if final_url:
            self.after(0, lambda: self._start_vlc(final_url, track_info, cover_img))
        else:
            print("[App] Failed to resolve stream for playback")

    def _start_vlc(self, url, track_info, cover_img):
        self.playback.play(url, track_info)
        self.player_bar.update_track_info(track_info, cover_img)
        self.current_cover_ref = cover_img # Prevent GC

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
        
        # Cover for file tagging
        cover_path = None
        if details.get("album", {}).get("cover"):
            try:
                uuid = details["album"]["cover"].replace('-', '/')
                curr_url = f"https://resources.tidal.com/images/{uuid}/1280x1280.jpg"
                r = requests.get(curr_url)
                if r.status_code == 200:
                    cover_path = os.path.join(target_dir, f"cover_{track_id}.jpg")
                    with open(cover_path, "wb") as f: f.write(r.content)
            except: pass

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
                    # For playback we keep temp file, for DL api_handler handles it usually? 
                    # Wait, api_handler.download_stream expects a URL (local file path is also a URL for ffmpeg).
                    # My previous code saved "temp_play" or "temp_dl".
                    prefix = "play" if is_playback else "dl"
                    temp_file = os.path.join(os.getcwd(), f"temp_{prefix}_{track_id}{ext}")
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
            win.destroy()
        
        ctk.CTkButton(win, text="Save", command=save).pack(pady=20)

    def on_closing(self):
        # Stop playback
        if hasattr(self, 'playback'):
            self.playback.stop()

        # Cleanup temp files
        print("[Cleanup] Cleaning up temporary files...")
        temp_files = glob.glob("temp_*.mpd") + glob.glob("temp_*.m3u8") + glob.glob("cover_*.jpg")
        for f in temp_files:
            try:
                os.remove(f)
                print(f"[Cleanup] Removed {f}")
            except Exception as e:
                print(f"[Cleanup] Failed to remove {f}: {e}")
                
        self.destroy()
        os._exit(0)

if __name__ == "__main__":
    app = TidalApp()
    app.mainloop()
