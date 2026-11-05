"""Frame extraction with FFmpeg."""

import shutil
import subprocess
from pathlib import Path
from typing import TypedDict

from strikelens_cv.ingest.config import IngestConfig

FRAME_PATTERN = "%06d.jpg"


class FrameEntry(TypedDict):
    index: int
    file: str
    timestamp_ms: int


def ffmpeg_binary() -> str:
    path = shutil.which("ffmpeg")
    if path is None:
        raise RuntimeError("FFmpeg is not installed or not on PATH (see docs/dev-setup.md)")
    return path


def ffmpeg_command(video: Path, frames_dir: Path, config: IngestConfig, ffmpeg: str) -> list[str]:
    """The FFmpeg call that writes one JPEG per 1/fps seconds.

    The fps filter gives output frame N the timestamp N / fps from the start of the
    file, and -frame_pts names the file after N. So the file name alone gives the
    time, with no rounding drift over a long fight.
    """
    return [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(video),
        "-vf",
        f"fps={config.fps}",
        "-frame_pts",
        "1",
        "-q:v",
        str(config.jpeg_quality),
        str(frames_dir / FRAME_PATTERN),
    ]


def frame_timestamp_ms(index: int, fps: float) -> int:
    """Time of frame `index` in ms from the start of the file."""
    if index < 0:
        raise ValueError("frame index must not be negative")
    return round(index * 1000 / fps)


def frame_manifest(frames_dir: Path, fps: float) -> list[FrameEntry]:
    """Every extracted frame, in order, with its timestamp."""
    entries: list[FrameEntry] = []
    for path in sorted(frames_dir.glob("*.jpg")):
        index = int(path.stem)
        entries.append(
            {"index": index, "file": path.name, "timestamp_ms": frame_timestamp_ms(index, fps)}
        )
    return entries


def extract_frames(video: Path, frames_dir: Path, config: IngestConfig) -> list[FrameEntry]:
    frames_dir.mkdir(parents=True, exist_ok=True)
    command = ffmpeg_command(video, frames_dir, config, ffmpeg_binary())
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg failed: {result.stderr.strip() or 'no error message'}")
    return frame_manifest(frames_dir, config.fps)
