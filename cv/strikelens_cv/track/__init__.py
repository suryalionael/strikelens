"""track stage: find the two fighters in every frame and keep them red and blue.

YOLO detects people and ByteTrack links them within each shot (detect.py, needs
the `detect` extra). The rest is pure: pick the two fighters in each shot and match
them to red and blue across camera cuts by the colour of their shorts (assign.py).

Output for one fight, under data/processed/<fight>/:

- detections.json   every person box with its shot, track ID, and colour feature
- tracks.json       per frame, the red and the blue box (or null), and per shot
                    which track IDs were red, blue, or dropped

Frames inside marked replays and non-fight segments are skipped.
"""

from strikelens_cv.track.assign import (
    assign_corners,
    build_tracks,
    feature_distance,
    pick_fighters,
    summarise_tracks,
)
from strikelens_cv.track.config import DEFAULT_TRACK_CONFIG, TrackConfig, load_track_config
from strikelens_cv.track.corrections import load_corrections, parse_corrections
from strikelens_cv.track.run import TrackResult, assign, label_frames, swaps, track, weights_path
from strikelens_cv.track.swaps import count_swaps, iou

__all__ = [
    "DEFAULT_TRACK_CONFIG",
    "TrackConfig",
    "TrackResult",
    "assign",
    "assign_corners",
    "build_tracks",
    "count_swaps",
    "feature_distance",
    "iou",
    "label_frames",
    "load_corrections",
    "load_track_config",
    "parse_corrections",
    "pick_fighters",
    "summarise_tracks",
    "swaps",
    "track",
    "weights_path",
]
