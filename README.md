# kozyfy

python gui app to search, stream, and download hi-res music from tidal using the hifi-api.

## features

*   **search**: find your fav tracks, albums, and artists.
*   **filtering**: only want hi-res? we got you. filter result by quality (hi-res, lossless, etc).
*   **playback**: full player bar with play, pause, seek, and volume controls (powered by vlc).
*   **downloads**: 
    *   saves tracks in native quality (`.flac` or `.m4a`).
    *   automatically embeds metadata and album art so your library looks good.
*   **ui**: dark mode aesthetics built with `customtkinter`.

## requirements

*   python 3.10+
*   **vlc media player** (you gotta have this installed for the music to actually play).
*   **ffmpeg** (needed if you want to download stuff).

## how to run

1.  clone this repo.
2.  install the python stuff:
    ```bash
    pip install -r tidal-gui/requirements.txt
    ```
3.  make sure ffmpeg is added to your computer's path.
4.  fire it up:
    ```bash
    python tidal-gui/tidal_gui.py
    ```

## disclaimer

just for educational purposes. please support the artists and keep your tidal subscription active. don't do anything shady.
