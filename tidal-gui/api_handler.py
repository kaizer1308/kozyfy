import requests
import subprocess
import threading
import json
import os
import re

class TidalApiHandler:
    def __init__(self, base_url="https://tidal-api.binimum.org"):
        self.base_url = base_url.rstrip("/")

    def set_base_url(self, url):
        self.base_url = url.rstrip("/")

    def search_tracks(self, query):
        """
        Search for tracks using the /search/ endpoint with param 's'.
        Returns a list of dicts (track info).
        """
        try:
            url = f"{self.base_url}/search/"
            params = {"s": query}
            headers = {"User-Agent": "TidalGui/1.0"}
            print(f"Searching: {url} with {params}")
            response = requests.get(url, params=params, headers=headers, timeout=10)
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
            return {"error": str(e)}

    def get_track_details(self, track_id):
        """Fetch full metadata for a track."""
        try:
            url = f"{self.base_url}/info/"
            params = {"id": track_id}
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json().get("data", {})
        except Exception as e:
            print(f"Error fetching details: {e}")
            return {}

    def get_stream_url(self, track_id, quality="HI_RES_LOSSLESS"):
        """
        Fetch playback info for a track ID using /track/.
        quality options: HI_RES_LOSSLESS, LOSSLESS, HIGH, LOW
        """
        try:
            url = f"{self.base_url}/track/"
            params = {
                "id": track_id,
                "quality": quality
            }
            headers = {"User-Agent": "TidalGui/1.0"}
            print(f"Fetching Stream: {url} with {params}")
            response = requests.get(url, params=params, headers=headers, timeout=15)
            print(f"Stream Response Status: {response.status_code}")
            
            if response.status_code == 403:
                return {"error": "403 Forbidden. The API blocked the request. If using a public instance, try another or use your local hifi-api."}
            
            response.raise_for_status()
            data = response.json()
            print(f"Stream Data: {json.dumps(data, indent=2)}") # Debug print
            
            # Data usually mimics playbackinfo response
            
            # Data usually mimics playbackinfo response
            # { "manifestMimeType": "...", "manifest": "..." }
            # But the hifi-api wrapper might wrap it.
            # Based on api_test.py, it expects 200 OK.
            # The hifi-api /track/ endpoint returns `resp.json()` from Tidal.
            
            return data
        except Exception as e:
            return {"error": str(e)}

    def download_stream(self, stream_url, output_path, metadata=None, cover_path=None, update_callback=None, duration=None):
        """
        Download the stream using ffmpeg with metadata and cover art.
        """
        if not stream_url:
            return False, "No stream URL provided"

        # Check for ffmpeg
        try:
            subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        except (FileNotFoundError, subprocess.CalledProcessError):
            return False, "FFmpeg is not installed or not in PATH."

        cmd = [
            "ffmpeg",
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
            
            # Use Popen to capture stderr in real-time
            # connect stdout to DEVNULL to avoid buffer filling up since we only read stderr
            process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, encoding='utf-8')
            
            time_pattern = re.compile(r"time=(\d{2}):(\d{2}):(\d{2})\.(\d{2})")
            
            while True:
                line = process.stderr.readline()
                if not line and process.poll() is not None:
                    break
                
                if line and update_callback and duration:
                    match = time_pattern.search(line)
                    if match:
                        h, m, s, ms = map(int, match.groups())
                        current_sec = h*3600 + m*60 + s + ms/100
                        percent = min((current_sec / duration) * 100, 99)
                        update_callback(percent)
            
            process.wait()
            
            if process.returncode == 0:
                if update_callback: update_callback(100)
                return True, "Download completed."
            else:
                err = process.stderr.read()
                return False, f"FFmpeg error: {err}"

        except Exception as e:
            return False, str(e)
