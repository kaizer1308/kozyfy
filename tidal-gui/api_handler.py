import requests
import subprocess
import threading
import json
import os
import re
import sys
import time
import logging
import queue
from requests.adapters import HTTPAdapter

logger = logging.getLogger("kozyfy.api")

class TidalApiHandler:
    def __init__(self, base_url="https://tidal-api.binimum.org"):
        self.base_url = base_url.rstrip("/")
        self._session = requests.Session()
        adapter = HTTPAdapter(pool_connections=20, pool_maxsize=20)
        self._session.mount("https://", adapter)
        self._session.mount("http://", adapter)
        self._default_headers = {"User-Agent": "TidalGui/1.0"}
        self._cache = {}
        self._cache_lock = threading.Lock()
        self._cache_ttl_sec = 300
        self.debug = False

    def set_base_url(self, url):
        self.base_url = url.rstrip("/")

    def _request(self, path, params=None, headers=None, timeout=10):
        url = f"{self.base_url}/{path.lstrip('/')}"
        merged_headers = dict(self._default_headers)
        if headers:
            merged_headers.update(headers)
        return self._session.get(url, params=params, headers=merged_headers, timeout=timeout)

    def _get_cached(self, cache_key):
        now = time.monotonic()
        with self._cache_lock:
            entry = self._cache.get(cache_key)
            if not entry:
                return None
            expires_at, value = entry
            if expires_at < now:
                del self._cache[cache_key]
                return None
            return value

    def _set_cached(self, cache_key, value, ttl=None):
        expires_at = time.monotonic() + (ttl or self._cache_ttl_sec)
        with self._cache_lock:
            self._cache[cache_key] = (expires_at, value)

    def search_tracks(self, query):
        """
        Search for tracks using the /search/ endpoint with param 's'.
        Returns a list of dicts (track info).
        """
        try:
            params = {"s": query}
            logger.info("Searching tracks | query=%s", query)
            response = self._request("search/", params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Tidal response for search/tracks often looks like:
            # { "items": [ ... ], "limit": 50, ... }
            # Or sometimes wrapped higher up.
            # hifi-api returns the direct response from Tidal.
            
            if "items" in data:
                return data["items"]
            elif "data" in data and "items" in data["data"]:
                 return data["data"]["items"]
            
            # Fallback for some wrappers
            return []
        except Exception as e:
            logger.exception("Search tracks failed | query=%s", query)
            return {"error": str(e)}

    def search_albums(self, query):
        """
        Search for albums using the /search/ endpoint with param 'al'.
        Returns a list of dicts (album info).
        """
        try:
            params = {"al": query}
            logger.info("Searching albums | query=%s", query)
            response = self._request("search/", params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Tidal response for top-hits with types=ALBUMS usually has "albums": { "items": ... }
            if "albums" in data and "items" in data["albums"]:
                return data["albums"]["items"]
            # Sometimes wrapped in "data"
            elif "data" in data and "albums" in data["data"] and "items" in data["data"]["albums"]:
                return data["data"]["albums"]["items"]
            
            return []
        except Exception as e:
            logger.exception("Search albums failed | query=%s", query)
            return {"error": str(e)}

    def get_track_details(self, track_id):
        """Fetch full metadata for a track."""
        try:
            cache_key = ("track_details", track_id)
            cached = self._get_cached(cache_key)
            if cached is not None:
                return cached
            params = {"id": track_id}
            response = self._request("info/", params=params, timeout=10)
            response.raise_for_status()
            payload = response.json().get("data", {})
            if payload:
                self._set_cached(cache_key, payload)
            return payload
        except Exception:
            logger.exception("Failed to fetch track details | track_id=%s", track_id)
            return {}

    def get_album(self, album_id):
        """
        Fetch album details including tracks.
        """
        try:
            cache_key = ("album", album_id)
            cached = self._get_cached(cache_key)
            if cached is not None:
                return cached
            params = {"id": album_id}
            logger.info("Fetching album | album_id=%s", album_id)
            response = self._request("album/", params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            # hifi-api returns { "data": { ...album_info, "items": [...] } }
            payload = data.get("data", {})
            if payload:
                self._set_cached(cache_key, payload)
            return payload
        except Exception:
            logger.exception("Failed to fetch album | album_id=%s", album_id)
            return {}

    def get_lyrics(self, track_id):
        """
        Fetch lyrics for a track ID using /lyrics/.
        Returns synced lyrics if available.
        """
        try:
            cache_key = ("lyrics", track_id)
            cached = self._get_cached(cache_key)
            if cached is not None:
                return cached
            params = {"id": track_id}
            logger.info("Fetching lyrics | track_id=%s", track_id)
            response = self._request("lyrics/", params=params, timeout=10)
            
            if response.status_code == 404:
                return {"error": "Lyrics not available for this track"}
            
            response.raise_for_status()
            data = response.json()
            payload = data.get("lyrics", {})
            if payload:
                self._set_cached(cache_key, payload)
            return payload
        except Exception:
            logger.exception("Failed to fetch lyrics | track_id=%s", track_id)
            return {"error": "Failed to fetch lyrics"}

    def get_stream_url(self, track_id, quality="HI_RES_LOSSLESS"):
        """
        Fetch playback info for a track ID using /track/.
        quality options: HI_RES_LOSSLESS, LOSSLESS, HIGH, LOW
        """
        try:
            params = {
                "id": track_id,
                "quality": quality
            }
            logger.info("Fetching stream | track_id=%s quality=%s", track_id, quality)
            response = self._request("track/", params=params, timeout=15)
            logger.debug("Stream response status: %s", response.status_code)
            
            if response.status_code == 403:
                return {"error": "403 Forbidden. The API blocked the request. If using a public instance, try another or use your local hifi-api."}
            
            response.raise_for_status()
            data = response.json()
            if self.debug:
                logger.debug("Stream data: %s", json.dumps(data, indent=2))
            
            # Data usually mimics playbackinfo response
            
            # Data usually mimics playbackinfo response
            # { "manifestMimeType": "...", "manifest": "..." }
            # But the hifi-api wrapper might wrap it.
            # Based on api_test.py, it expects 200 OK.
            # The hifi-api /track/ endpoint returns `resp.json()` from Tidal.
            
            return data
        except Exception:
            logger.exception("Failed to fetch stream | track_id=%s", track_id)
            return {"error": "Failed to fetch stream"}

    def download_stream(self, stream_url, output_path, metadata=None, cover_path=None, update_callback=None, duration=None, cancel_event=None):
        """
        Download the stream using ffmpeg with metadata and cover art.
        """
        if not stream_url:
            return False, "No stream URL provided"

        # Get FFmpeg path using dependency checker
        try:
            from utils.dependencies import get_ffmpeg_path
            ffmpeg_path = get_ffmpeg_path()
        except ImportError:
            ffmpeg_path = None
        
        if not ffmpeg_path:
            # Fallback to checking PATH directly
            import shutil
            ffmpeg_path = shutil.which("ffmpeg")
        
        if not ffmpeg_path:
            return False, "FFmpeg is not installed or not in PATH. Please install FFmpeg."

        # Windows subprocess creation flags to hide console window
        creationflags = 0
        if sys.platform == "win32":
            creationflags = subprocess.CREATE_NO_WINDOW

        cmd = [
            ffmpeg_path,
            "-protocol_whitelist", "file,http,https,tcp,tls,crypto,data",
            "-i", stream_url
        ]

        if cover_path and os.path.exists(cover_path):
            cmd.extend(["-i", cover_path])
            cmd.extend(["-map", "0:0"]) # Map Audio
            cmd.extend(["-map", "1:0"]) # Map Cover
            cmd.extend(["-c:v", "copy"]) # Copy image data
            
            # Set metadata for cover
            cmd.extend(["-disposition:v:0", "attached_pic"])
            cmd.extend(["-metadata:s:v", 'title="Album cover"'])
            cmd.extend(["-metadata:s:v", 'comment="Cover (front)"'])
        else:
            cmd.extend(["-c", "copy"])

        if metadata:
            for key, value in metadata.items():
                if value:
                     cmd.extend(["-metadata", f"{key}={value}"])

        cmd.extend([
            "-c:a", "copy",
            "-y",
            "-loglevel", "info", # Increased log level for progress parsing
            output_path
        ])

        try:
            if update_callback:
                update_callback(0) # Start with 0%
            if cancel_event and cancel_event.is_set():
                return False, "Cancelled"

            # Use Popen to capture stderr in real-time
            # Use CREATE_NO_WINDOW on Windows to hide console
            # Use errors='replace' for encoding to handle non-UTF8 output
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.DEVNULL, 
                stderr=subprocess.PIPE, 
                text=True, 
                encoding='utf-8',
                errors='replace',
                creationflags=creationflags
            )

            stderr_queue = queue.Queue()
            stderr_lines = []

            def _read_stderr():
                for line in iter(process.stderr.readline, ''):
                    if not line:
                        break
                    stderr_lines.append(line)
                    stderr_queue.put(line)

            threading.Thread(target=_read_stderr, daemon=True).start()

            time_pattern = re.compile(r"time=(\d{2}):(\d{2}):(\d{2})\.(\d{2})")

            while True:
                if cancel_event and cancel_event.is_set():
                    process.terminate()
                    break

                try:
                    line = stderr_queue.get(timeout=0.1)
                except queue.Empty:
                    if process.poll() is not None:
                        break
                    continue

                if line and update_callback and duration:
                    match = time_pattern.search(line)
                    if match:
                        h, m, s, ms = map(int, match.groups())
                        current_sec = h*3600 + m*60 + s + ms/100
                        percent = min((current_sec / duration) * 100, 99)
                        update_callback(percent)
            
            process.wait()

            if cancel_event and cancel_event.is_set():
                return False, "Cancelled"

            if process.returncode == 0:
                if update_callback: update_callback(100)
                return True, "Download completed."
            else:
                err = "".join(stderr_lines)
                return False, f"FFmpeg error: {err}"

        except Exception as e:
            return False, str(e)
