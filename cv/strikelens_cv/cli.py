"""Command-line entry point: `strikelens-cv`."""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from strikelens_cv import __version__
from strikelens_cv.ingest.config import DEFAULT_CONFIG
from strikelens_cv.segments.config import DEFAULT_SEGMENT_CONFIG


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


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "ingest":
        return run_ingest(args)
    if args.command == "suggest":
        return run_suggest(args)
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
