"""Run tracking for one fight: files in, files out. The logic lives in assign.py."""

import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from strikelens_cv import __version__
from strikelens_cv.ingest.cuts import Shot
from strikelens_cv.paths import models_dir, processed_dir
from strikelens_cv.segments import Segment, in_segment, load_segments
from strikelens_cv.track.assign import (
    Assignment,
    Detection,
    FrameInfo,
    TrackFrame,
    assign_corners,
    build_tracks,
    summarise_tracks,
)
from strikelens_cv.track.config import TrackConfig
from strikelens_cv.track.corrections import Corrections, load_corrections
from strikelens_cv.track.referee import RefereeReport, is_referee, referee_report
from strikelens_cv.track.swaps import SwapReport, count_swaps

WEIGHTS_HELP = (
    "Download it from https://github.com/ultralytics/assets/releases and save it in "
    "models/ (gitignored), or set `weights` in cv/configs/track.toml."
)


@dataclass(frozen=True)
class TrackResult:
    out_dir: Path
    assignment: Assignment
    frames: list[TrackFrame]


def label_frames(
    frames: Sequence[dict[str, Any]], shots: Sequence[Shot], segments: Sequence[Segment]
) -> list[FrameInfo]:
    """Give each frame its shot and say whether it is inside a marked segment.

    A frame on a cut belongs to the shot that starts there. Frames after the last
    shot's end (rounding at the very end of the file) belong to the last shot.
    """
    out: list[FrameInfo] = []
    for f in frames:
        t = f["timestamp_ms"]
        shot = next(
            (s["index"] for s in shots if s["start_ms"] <= t < s["end_ms"]),
            shots[-1]["index"] if shots else 0,
        )
        out.append(
            {
                "index": f["index"],
                "timestamp_ms": t,
                "shot": shot,
                "skipped": in_segment(t, segments),
            }
        )
    return out


def _read(path: Path, hint: str) -> Any:
    if not path.is_file():
        raise FileNotFoundError(f"{path} not found; {hint}")
    return json.loads(path.read_text())


def _write(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n")


def weights_path(config: TrackConfig) -> Path:
    """The weights file in models/. Missing weights are an error, never a download."""
    path = models_dir() / config.weights
    if not path.is_file():
        raise FileNotFoundError(f"no YOLO weights at {path}. {WEIGHTS_HELP}")
    return path


def track(fight: str, config: TrackConfig, corrections: Path | None = None) -> TrackResult:
    """Detect and track people, then assign red and blue. Needs the detect extra."""
    from strikelens_cv.track.detect import detect

    out_dir = processed_dir(fight)
    manifest = _read(out_dir / "frames.json", "run strikelens-cv ingest first")
    cuts = _read(out_dir / "cuts.json", "run strikelens-cv ingest first")
    fight_json = out_dir / "fight.json"
    segments = load_segments(fight_json) if fight_json.is_file() else []
    weights = weights_path(config)

    frames = label_frames(manifest["frames"], cuts["shots"], segments)
    files = {f["index"]: f["file"] for f in manifest["frames"]}
    detections = detect(out_dir / "frames", frames, files, weights, config)
    _write(
        out_dir / "detections.json",
        {
            "strikelens_cv": __version__,
            "config": config.as_dict(),
            "frames": frames,
            "detections": detections,
        },
    )
    return assign(fight, config, corrections)


def _assignment(
    data: dict[str, Any], config: TrackConfig, corrections: Corrections | None
) -> tuple[Assignment, list[TrackFrame]]:
    detections: list[Detection] = data["detections"]
    assignment = assign_corners(
        summarise_tracks(detections),
        config,
        corrections,
        is_excluded=lambda track: is_referee(track, config),
    )
    return assignment, build_tracks(data["frames"], detections, assignment)


def assign(fight: str, config: TrackConfig, corrections: Path | None = None) -> TrackResult:
    """Redo red and blue from detections.json, for example after adding corrections."""
    out_dir = processed_dir(fight)
    data = _read(out_dir / "detections.json", "run strikelens-cv track first")
    fixes = load_corrections(corrections) if corrections else None
    assignment, frames = _assignment(data, config, fixes)
    _write(
        out_dir / "tracks.json",
        {
            "strikelens_cv": __version__,
            "seeded_by": assignment["seeded_by"],
            "corrections": corrections.name if corrections else None,
            "shots": assignment["shots"],
            "frames": frames,
        },
    )
    return TrackResult(out_dir=out_dir, assignment=assignment, frames=frames)


def swaps(fight: str, config: TrackConfig, corrections: Path) -> SwapReport:
    """Swaps in the automatic assignment, against the same detections corrected."""
    data = _read(processed_dir(fight) / "detections.json", "run strikelens-cv track first")
    _, auto = _assignment(data, config, None)
    _, truth = _assignment(data, config, load_corrections(corrections))
    return count_swaps(auto, truth)


def referee(fight: str, config: TrackConfig, corrections: Path) -> RefereeReport:
    """How well the referee filter does, with the corrections as the truth."""
    data = _read(processed_dir(fight) / "detections.json", "run strikelens-cv track first")
    return referee_report(
        summarise_tracks(data["detections"]), load_corrections(corrections), config
    )
