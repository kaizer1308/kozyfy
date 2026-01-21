"""
Profiling harness for Kozyfy.
Profiles CPU and memory for UI rendering and API cache behavior.
"""
from __future__ import annotations

import argparse
import cProfile
import os
import pstats
import sys
import time
import tracemalloc


ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import customtkinter as ctk

from api_handler import TidalApiHandler
from ui.search_view import SearchResultsView
from utils.paths import get_temp_dir


def build_items(count: int) -> list[dict]:
    items = []
    for i in range(count):
        tags = []
        if i % 10 == 0:
            tags.append("HIRES_LOSSLESS")
        elif i % 7 == 0:
            tags.append("MQA")
        audio_modes = ["stereo"] if i % 2 == 0 else []
        items.append(
            {
                "id": i,
                "title": f"Track {i}",
                "artist": {"name": f"Artist {i % 25}"},
                "album": {"title": f"Album {i % 50}"},
                "duration": 180 + (i % 240),
                "audioQuality": "LOSSLESS" if i % 5 == 0 else "HIGH",
                "mediaMetadata": {"tags": tags},
                "audioModes": audio_modes,
                "_type": "TRACK",
            }
        )
    return items


def wait_for_render(root: ctk.CTk, view: SearchResultsView, timeout_sec: float) -> None:
    end_time = time.monotonic() + timeout_sec
    while time.monotonic() < end_time:
        root.update()
        if view._render_job is None and not view._pending_items:
            return
        time.sleep(0.005)
    raise TimeoutError("Render did not finish within timeout.")


def profile_workload(name: str, func, output_dir: str, sort_key: str, top: int) -> None:
    os.makedirs(output_dir, exist_ok=True)
    profile_path = os.path.join(output_dir, f"{name}.prof")
    stats_path = os.path.join(output_dir, f"{name}.txt")

    profiler = cProfile.Profile()
    tracemalloc.start()
    start_snapshot = tracemalloc.take_snapshot()

    start_time = time.perf_counter()
    profiler.enable()
    func()
    profiler.disable()
    duration = time.perf_counter() - start_time

    current, peak = tracemalloc.get_traced_memory()
    end_snapshot = tracemalloc.take_snapshot()
    tracemalloc.stop()

    profiler.dump_stats(profile_path)
    stats = pstats.Stats(profiler).sort_stats(sort_key)

    with open(stats_path, "w", encoding="utf-8") as handle:
        stats.stream = handle
        stats.print_stats(top)
        handle.write("\n")
        handle.write(f"Elapsed: {duration:.3f}s\n")
        handle.write(f"Current mem: {current / 1024:.1f} KiB\n")
        handle.write(f"Peak mem: {peak / 1024:.1f} KiB\n")
        handle.write("\nTop memory growth:\n")
        for stat in end_snapshot.compare_to(start_snapshot, "lineno")[:10]:
            handle.write(f"{stat}\n")

    print(f"Saved profile to {profile_path}")
    print(f"Saved stats to {stats_path}")


def profile_render(args: argparse.Namespace) -> None:
    def _workload():
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")
        root = ctk.CTk()
        root.withdraw()
        view = SearchResultsView(root, on_play=lambda *_: None, on_download=lambda *_: None)
        view.pack(fill="both", expand=True)
        if args.batch_size is not None:
            view._render_batch_size = args.batch_size
        if args.interval_ms is not None:
            view._render_interval_ms = args.interval_ms
        items = build_items(args.items)
        try:
            view.populate(items)
            wait_for_render(root, view, args.timeout)
        finally:
            root.destroy()

    profile_workload("render", _workload, args.output_dir, args.sort, args.top)


def profile_cache(args: argparse.Namespace) -> None:
    def _workload():
        api = TidalApiHandler()
        if args.cache_max is not None:
            api._cache_max_entries = args.cache_max
        for i in range(args.entries):
            payload = {"id": i, "title": f"Track {i}"}
            api._set_cached(("bench", i), payload, ttl=60)
        for i in range(args.entries):
            api._get_cached(("bench", i))

    profile_workload("cache", _workload, args.output_dir, args.sort, args.top)


def parse_args() -> argparse.Namespace:
    default_output = os.path.join(get_temp_dir(), "profiling")
    parser = argparse.ArgumentParser(description="Kozyfy profiling harness")
    subparsers = parser.add_subparsers(dest="mode", required=True)

    render_parser = subparsers.add_parser("render", help="Profile search results rendering")
    render_parser.add_argument("--items", type=int, default=500, help="Number of items to render")
    render_parser.add_argument("--batch-size", type=int, default=None, help="Override render batch size")
    render_parser.add_argument("--interval-ms", type=int, default=None, help="Override render interval in ms")
    render_parser.add_argument("--timeout", type=float, default=10.0, help="Timeout in seconds")
    render_parser.add_argument("--output-dir", default=default_output, help="Directory for profile output")
    render_parser.add_argument("--sort", default="tottime", help="pstats sort key")
    render_parser.add_argument("--top", type=int, default=30, help="Top functions to print")
    render_parser.set_defaults(handler=profile_render)

    cache_parser = subparsers.add_parser("cache", help="Profile API cache usage")
    cache_parser.add_argument("--entries", type=int, default=2000, help="Cache entries to set/get")
    cache_parser.add_argument("--cache-max", type=int, default=None, help="Override cache max entries")
    cache_parser.add_argument("--output-dir", default=default_output, help="Directory for profile output")
    cache_parser.add_argument("--sort", default="tottime", help="pstats sort key")
    cache_parser.add_argument("--top", type=int, default=30, help="Top functions to print")
    cache_parser.set_defaults(handler=profile_cache)

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.handler(args)


if __name__ == "__main__":
    main()
