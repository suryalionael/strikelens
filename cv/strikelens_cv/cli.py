"""Command-line entry point: `strikelens-cv`."""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING

from strikelens_cv import __version__
from strikelens_cv.ingest.config import DEFAULT_CONFIG
from strikelens_cv.overlay.config import DEFAULT_OVERLAY_CONFIG
from strikelens_cv.pose.config import DEFAULT_POSE_CONFIG
from strikelens_cv.rounds.config import DEFAULT_ROUNDS_CONFIG
from strikelens_cv.segments.config import DEFAULT_SEGMENT_CONFIG
from strikelens_cv.segments.core import in_round
from strikelens_cv.strikes.config import DEFAULT_WINDOWS_CONFIG
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

    rounds = commands.add_parser(
        "rounds",
        help="suggest rounds from the broadcast scoreboard (needs the ingest extra)",
        description="Find when the scoreboard is on screen in the extracted frames and "
        "write round-suggestions.json to data/processed/<fight>/. The tagger loads it.",
    )
    rounds.add_argument("--fight", required=True, help="fight name used at ingest")
    rounds.add_argument(
        "--config", type=Path, default=DEFAULT_ROUNDS_CONFIG, help="TOML settings file"
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
    referee = commands.add_parser(
        "referee",
        help="measure the referee filter against a corrections file",
        description="Share of referee tracks removed and of fighter tracks wrongly "
        "removed. Tracks corrected to none count as the referee.",
    )
    for command in (track, assign, swaps, referee):
        command.add_argument("--fight", required=True, help="fight name used at ingest")
        command.add_argument(
            "--config", type=Path, default=DEFAULT_TRACK_CONFIG, help="TOML settings file"
        )
    for command in (track, assign):
        command.add_argument("--corrections", type=Path, help="track-corrections.json")
    for command in (swaps, referee):
        command.add_argument(
            "--corrections", type=Path, required=True, help="track-corrections.json"
        )

    pose = commands.add_parser(
        "pose",
        help="keypoints for red and blue in every frame (needs the pose extra)",
        description="Run the pose backend on each fighter box from tracks.json and "
        "write keypoints/red.json and keypoints/blue.json to data/processed/<fight>/.",
    )
    windows = commands.add_parser(
        "windows",
        help="training windows from confirmed tags and keypoints",
        description="Cut keypoint windows around confirmed tags (labelled with the weapon), "
        "rejected suggestions, and times with no strike, for one or more fights. Writes "
        "data/labels/windows/<name>/windows.jsonl and manifest.json.",
    )
    windows.add_argument(
        "--fight", action="append", required=True, help="fight name used at ingest (repeat)"
    )
    windows.add_argument("--name", required=True, help="name of this window set, e.g. v1")
    windows.add_argument(
        "--config", type=Path, default=DEFAULT_WINDOWS_CONFIG, help="TOML settings file"
    )

    pose.add_argument("--fight", required=True, help="fight name used at ingest")
    pose.add_argument("--config", type=Path, default=DEFAULT_POSE_CONFIG, help="TOML settings file")

    overlay = commands.add_parser(
        "overlay",
        help="render boxes, skeletons, and the strike timeline onto video",
        description="Draw the red and blue boxes, skeletons, and a timeline of confirmed "
        "tags onto the extracted frames, and write an MP4 to data/processed/<fight>/. "
        "With --ids, draw every person with shot and track ID instead.",
    )
    overlay.add_argument("--fight", required=True, help="fight name used at ingest")
    overlay.add_argument("--round", type=int, help="only this round (from fight.json)")
    overlay.add_argument(
        "--ids", action="store_true", help="label every person with shot and track ID"
    )
    overlay.add_argument(
        "--config", type=Path, default=DEFAULT_OVERLAY_CONFIG, help="TOML settings file"
    )
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


def _clock(ms: int) -> str:
    return f"{ms // 60_000}:{ms // 1000 % 60:02}"


def run_rounds(args: argparse.Namespace) -> int:
    from strikelens_cv.rounds import load_rounds_config, suggest_fight_rounds

    try:
        path, suggestions = suggest_fight_rounds(args.fight, load_rounds_config(args.config))
    except (FileNotFoundError, RuntimeError, ValueError) as error:
        print(f"strikelens-cv rounds: {error}", file=sys.stderr)
        return 1
    for r in suggestions:
        flag = " (partial?)" if r["partial"] else ""
        print(f"Round {r['number']}: {_clock(r['start_ms'])} to {_clock(r['end_ms'])}{flag}")
    if not suggestions:
        print("No scoreboard found. Mark the rounds by hand, or check scoreboard_region.")
    print(f"Written to {path}")
    return 0


def _report_tracks(result: "TrackResult") -> None:
    shots = result.assignment["shots"]
    uncertain = sum(1 for s in shots if s["uncertain"])
    by_kit = sum(1 for s in shots if s["by_kit"])
    seen = sum(1 for f in result.frames if f["red"] or f["blue"])
    print(
        f"{seen} of {len(result.frames)} frames have a fighter, {len(shots)} shots, "
        f"{uncertain} uncertain. Written to {result.out_dir / 'tracks.json'}"
    )
    print(f"{by_kit} of {len(shots)} shots decided by kit colour.")
    if result.rounds:
        inside = sum(1 for f in result.frames if in_round(f["timestamp_ms"], result.rounds))
        count = len(result.rounds)
        print(f"Tracked inside {count} {'round' if count == 1 else 'rounds'}: {inside} frames.")
    else:
        print(
            "No rounds in fight.json: tracked the whole video. Mark the rounds in the "
            "tagger and save the fight as fight.json."
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


def _percent(share: float | None) -> str:
    return "n/a" if share is None else f"{share:.0%}"


def run_referee(args: argparse.Namespace) -> int:
    from strikelens_cv.track import load_track_config, referee

    try:
        report = referee(args.fight, load_track_config(args.config), args.corrections)
    except (FileNotFoundError, ValueError) as error:
        print(f"strikelens-cv referee: {error}", file=sys.stderr)
        return 1
    print(
        f"Referee tracks removed: {_percent(report['referee_removed'])} "
        f"of {report['referee_tracks']}. Fighter tracks wrongly removed: "
        f"{_percent(report['fighter_removed'])} of {report['fighter_tracks']}."
    )
    return 0


def run_pose(args: argparse.Namespace) -> int:
    from strikelens_cv.pose import count_missing, load_pose_config, pose

    try:
        result = pose(args.fight, load_pose_config(args.config))
    except (FileNotFoundError, RuntimeError, ValueError) as error:
        print(f"strikelens-cv pose: {error}", file=sys.stderr)
        return 1
    for corner, frames in result.frames.items():
        counts = count_missing(frames)
        print(
            f"{corner}: keypoints in {counts['found']} of {len(frames)} frames "
            f"(no box {counts['no_box']}, no pose {counts['no_pose']}, "
            f"skipped {counts['skipped']})"
        )
    print(f"Written to {result.out_dir}")
    return 0


def run_overlay(args: argparse.Namespace) -> int:
    from strikelens_cv.overlay import load_overlay_config, overlay

    try:
        result = overlay(args.fight, load_overlay_config(args.config), args.round, args.ids)
    except (FileNotFoundError, RuntimeError, ValueError) as error:
        print(f"strikelens-cv overlay: {error}", file=sys.stderr)
        return 1
    print(
        f"{result.frames} frames and {result.tags} confirmed "
        f"{'tag' if result.tags == 1 else 'tags'} written to {result.path}"
    )
    if not result.rounds:
        print("No rounds in fight.json: rendered every frame that was tracked.")
    if not args.ids and not result.keypoints:
        print("No keypoints/ for this fight: boxes only. Run strikelens-cv pose for skeletons.")
    if result.tags == 0:
        print(
            "No confirmed tags: the timeline is empty. Save them from the API as tags.json "
            "(see cv/README.md, Overlay)."
        )
    print("Check docs/data-policy.md before sharing this video outside the team.")
    return 0


def run_windows(args: argparse.Namespace) -> int:
    from strikelens_cv.strikes import build_windows, load_windows_config

    try:
        result = build_windows(args.name, args.fight, load_windows_config(args.config))
    except (FileNotFoundError, KeyError, ValueError) as error:
        print(f"strikelens-cv windows: {error}", file=sys.stderr)
        return 1
    for split, labels in result.manifest["counts"].items():
        parts = ", ".join(f"{label} {count}" for label, count in labels.items())
        print(f"{split}: {sum(labels.values())} windows ({parts})")
    splits = set(result.manifest["fights"].values())
    if len(splits) < 2:
        print(
            f"All fights are in {splits.pop() if splits else 'no'} split. Add fights to have both."
        )
    print(f"Written to {result.out_dir}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "ingest":
        return run_ingest(args)
    if args.command == "suggest":
        return run_suggest(args)
    if args.command == "rounds":
        return run_rounds(args)
    if args.command in ("track", "assign"):
        return run_track(args, redo_only=args.command == "assign")
    if args.command == "swaps":
        return run_swaps(args)
    if args.command == "referee":
        return run_referee(args)
    if args.command == "pose":
        return run_pose(args)
    if args.command == "windows":
        return run_windows(args)
    if args.command == "overlay":
        return run_overlay(args)
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
