"""strikes stage: from confirmed tags to training data, and later suggestions.

windows.py cuts fixed-length keypoint windows around confirmed tags (labelled
with the weapon) and around times with no strike (pure). run.py reads each
fight's keypoints and tags.json and writes, under data/labels/windows/<name>/
(gitignored):

- windows.jsonl   one window per line: fight, split, kind, label, fighter, samples
- manifest.json   keypoint format, landmarks, settings, fight splits, and counts
"""

from strikelens_cv.strikes.config import DEFAULT_WINDOWS_CONFIG, WindowsConfig, load_windows_config
from strikelens_cv.strikes.run import WindowsResult, build_windows, windows_dir
from strikelens_cv.strikes.windows import (
    Window,
    cut_window,
    fight_windows,
    normalise,
    sample_times,
    split_for,
    summary,
)

__all__ = [
    "DEFAULT_WINDOWS_CONFIG",
    "Window",
    "WindowsConfig",
    "WindowsResult",
    "build_windows",
    "cut_window",
    "fight_windows",
    "load_windows_config",
    "normalise",
    "sample_times",
    "split_for",
    "summary",
    "windows_dir",
]
