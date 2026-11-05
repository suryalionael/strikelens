"""Run the whole ingest stage for one fight."""

import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from strikelens_cv import __version__
from strikelens_cv.ingest.config import IngestConfig
from strikelens_cv.ingest.cuts import Shot, detect_scenes, shots_from_scenes
from strikelens_cv.ingest.frames import FrameEntry, extract_frames
from strikelens_cv.paths import processed_dir
from strikelens_cv.segments.config import SegmentConfig
from strikelens_cv.segments.run import write_suggestions


@dataclass(frozen=True)
class IngestResult:
    out_dir: Path
    frames: list[FrameEntry]
    shots: list[Shot]


def _write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n")


def ingest(
    video: Path,
    fight: str,
    config: IngestConfig,
    overwrite: bool = False,
    segment_config: SegmentConfig | None = None,
) -> IngestResult:
    """Extract frames, find cuts, and suggest replays. Output goes to data/processed/<fight>/."""
    if not video.is_file():
        raise FileNotFoundError(f"video not found: {video}")
    out_dir = processed_dir(fight)
    frames_dir = out_dir / "frames"
    if frames_dir.exists():
        if not overwrite:
            raise FileExistsError(f"{out_dir} already has frames; pass --overwrite to redo them")
        shutil.rmtree(frames_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    frames = extract_frames(video, frames_dir, config)
    scenes, duration_ms = detect_scenes(video, config)
    shots = shots_from_scenes(scenes, duration_ms, config.min_shot_ms)

    _write_json(out_dir / "frames.json", {"fps": config.fps, "frames": frames})
    _write_json(out_dir / "cuts.json", {"duration_ms": duration_ms, "shots": shots})
    write_suggestions(out_dir, shots, segment_config or SegmentConfig())
    _write_json(
        out_dir / "ingest.json",
        {
            # File name only: the video itself never leaves the analyst's machine.
            "video_file": video.name,
            "strikelens_cv": __version__,
            "config": config.as_dict(),
            "frame_count": len(frames),
            "shot_count": len(shots),
        },
    )
    return IngestResult(out_dir=out_dir, frames=frames, shots=shots)
