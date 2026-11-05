"""Command-line entry point: `strikelens-cv`."""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING

from strikelens_cv import __version__
from strikelens_cv.ingest.config import DEFAULT_CONFIG
from strikelens_cv.segments.config import DEFAULT_SEGMENT_CONFIG
from strikelens_cv.track.config import DEFAULT_TRACK_CONFIG

if TYPE_CHECKING:
    from strikelens_cv.track import TrackResult


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="strikelens-cv",
        description="StrikeLens computer vision pipeline.",
    )
    parser.add_argument("--version", action="version", version=f"strikelens-cv {__version__}")
    commands = parser.add_subparsers(dest="command")

    ingest = commands.add_parser(
        "ingest",
        help="extract frames and find camera cuts",
        description="Extract frames with FFmpeg and find camera cuts. "
        "Writes to data/processed/<fight>/.",
    )
    ingest.add_argument("video", type=Path, help="local fight video file")
    ingest.add_argument("--fight", required=True, help="fight name, used for the output folder")
    ingest.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="TOML settings file")
    ingest.add_argument("--overwrite", action="store_true", help="redo frames that exist")
    ingest.add_argument(
        "--segment-config",
        type=Path,
        default=DEFAULT_SEGMENT_CONFIG,
        help="TOML settings for replay suggestions",
    )

    suggest = commands.add_parser(
        "suggest",
        help="suggest likely replays from an existing cut list",
        description="Read data/processed/<fight>/cuts.json and write "
        "segment-suggestions.json next to it. The tagger loads that file.",
    )
    suggest.add_argument("--fight", required=True, help="fight name used at ingest")
    suggest.add_argument(
        "--config", type=Path, default=DEFAULT_SEGMENT_CONFIG, help="TOML settings file"
    )

    track = commands.add_parser(
        "track",
        help="find the two fighters in every frame (needs the detect extra)",
        description="Detect and track people with YOLO and ByteTrack, shot by shot, then "
        "assign red and blue. Reads the ingest output and writes detections.json and "
        "tracks.json to data/processed/<fight>/.",
    )
    assign = commands.add_parser(
        "assign",
        help="redo red and blue from detections.json, for example with corrections",
        description="Re-run the red and blue assignment without detecting again.",
    )
    swaps = commands.add_parser(
        "swaps",
        help="count red and blue swaps against a corrections file",
        description="Compare the automatic assignment with the same detections "
        "corrected by hand, and count how often red and blue were swapped.",
    )
    for command in (track, assign, swaps):
        command.add_argument("--fight", required=True, help="fight name used at ingest")
        command.add_argument(
            "--config", type=Path, default=DEFAULT_TRACK_CONFIG, help="TOML settings file"
        )
    for command in (track, assign):
        command.add_argument("--corrections", type=Path, help="track-corrections.json")
    swaps.add_argument("--corrections", type=Path, required=True, help="track-corrections.json")
    return parser


def run_ingest(args: argparse.Namespace) -> int:
    # Imported here so `--version` and `--help` work without the ingest extra.
    from strikelens_cv.ingest import ingest, load_config
    from strikelens_cv.segments import load_segment_config

    try:
        result = ingest(
            args.video,
            args.fight,
            load_config(args.config),
            args.overwrite,
            load_segment_config(args.segment_config),
        )
    except (FileNotFoundError, FileExistsError, RuntimeError, ValueError) as error:
        print(f"strikelens-cv ingest: {error}", file=sys.stderr)
        return 1
    cuts = len(result.shots) - 1
    print(
        f"{len(result.frames)} frames and {cuts} {'cut' if cuts == 1 else 'cuts'} "
        f"written to {result.out_dir}"
    )
    return 0


def run_suggest(args: argparse.Namespace) -> int:
    from strikelens_cv.segments import load_segment_config, suggest

    try:
        path, suggestions = suggest(args.fight, load_segment_config(args.config))
    except (FileNotFoundError, ValueError) as error:
        print(f"strikelens-cv suggest: {error}", file=sys.stderr)
        return 1
    count = len(suggestions)
    print(f"{count} likely {'replay' if count == 1 else 'replays'} written to {path}")
    return 0


def _report_tracks(result: "TrackResult") -> None:
    shots = result.assignment["shots"]
    uncertain = sum(1 for s in shots if s["uncertain"])
    seen = sum(1 for f in result.frames if f["red"] or f["blue"])
    print(
        f"{seen} of {len(result.frames)} frames have a fighter, {len(shots)} shots, "
        f"{uncertain} uncertain. Written to {result.out_dir / 'tracks.json'}"
    )
    if result.assignment["seeded_by"] == "left_is_red":
        print("Red was guessed as the fighter on the left in the first shot. Check it.")


def run_track(args: argparse.Namespace, redo_only: bool) -> int:
    from strikelens_cv.track import assign, load_track_config, track

    name = "assign" if redo_only else "track"
    try:
        config = load_track_config(args.config)
        result = (assign if redo_only else track)(args.fight, config, args.corrections)
    except (FileNotFoundError, RuntimeError, ValueError) as error:
        print(f"strikelens-cv {name}: {error}", file=sys.stderr)
        return 1
    _report_tracks(result)
    return 0


def run_swaps(args: argparse.Namespace) -> int:
    from strikelens_cv.track import load_track_config, swaps

    try:
        report = swaps(args.fight, load_track_config(args.config), args.corrections)
    except (FileNotFoundError, ValueError) as error:
        print(f"strikelens-cv swaps: {error}", file=sys.stderr)
        return 1
    print(
        f"{report['swaps']} {'swap' if report['swaps'] == 1 else 'swaps'}, "
        f"{report['swapped_frames']} of {report['compared_frames']} compared frames swapped"
    )
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "ingest":
        return run_ingest(args)
    if args.command == "suggest":
        return run_suggest(args)
    if args.command in ("track", "assign"):
        return run_track(args, redo_only=args.command == "assign")
    if args.command == "swaps":
        return run_swaps(args)
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
