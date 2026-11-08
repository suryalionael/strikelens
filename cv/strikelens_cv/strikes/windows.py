"""Training windows: keypoints around confirmed tags, and around times with no strike.

Pure: plain lists and dicts in and out, so it is tested in CI. run.py reads the
keypoint and tag files and writes the windows.

Positive windows are cut around each confirmed tag, for the fighter who threw it,
and labelled with the weapon. Negative windows come from rejected suggestions and
from round time well away from any tag of that fighter. Keypoints are normalised
to the fighter's box, so a window does not depend on where the fighter stands or
how far the camera is. Samples without keypoints stay missing (null), never zeros.
"""

import hashlib
import random
from bisect import bisect_left
from collections.abc import Mapping, Sequence
from typing import Any, Literal, TypedDict

from strikelens_cv.strikes.config import WindowsConfig

Corner = Literal["red", "blue"]
Kind = Literal["strike", "rejected", "background"]
Split = Literal["train", "validation"]
Keypoint = list[float]  # [x, y, z, visibility]


class Window(TypedDict):
    fight: str
    split: Split
    kind: Kind
    label: str  # the weapon for a strike, "none" otherwise
    fighter: Corner
    tag_id: str | None
    center_ms: int
    samples: list[list[Keypoint] | None]


def normalise(keypoints: Sequence[Sequence[float]], box: Sequence[float]) -> list[Keypoint]:
    """Keypoints relative to the box: centre at 0, box height 1. Visibility kept."""
    cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    height = max(1.0, box[3] - box[1])
    return [
        [
            round((x - cx) / height, 4),
            round((y - cy) / height, 4),
            round(z / height, 4),
            round(v, 3),
        ]
        for x, y, z, v in keypoints
    ]


def sample_times(center_ms: int, config: WindowsConfig) -> list[float]:
    """`samples` evenly spaced times from `before_ms` before to `after_ms` after."""
    start, span = center_ms - config.before_ms, config.before_ms + config.after_ms
    step = span / (config.samples - 1)
    return [start + i * step for i in range(config.samples)]


def cut_window(
    frames: Sequence[Mapping[str, Any]], center_ms: int, config: WindowsConfig
) -> list[list[Keypoint] | None]:
    """Normalised keypoints at each sample time, from the nearest frame.

    `frames` are one fighter's keypoint frames in time order. A sample is missing
    when the nearest frame has no keypoints, or is further away than a sample step.
    """
    times = [f["timestamp_ms"] for f in frames]
    reach = (config.before_ms + config.after_ms) / (config.samples - 1)
    out: list[list[Keypoint] | None] = []
    for t in sample_times(center_ms, config):
        i = bisect_left(times, t)
        near = [j for j in (i - 1, i) if 0 <= j < len(frames)]
        if not near:
            out.append(None)
            continue
        j = min(near, key=lambda j: abs(times[j] - t))
        frame = frames[j]
        if abs(times[j] - t) > reach or frame.get("keypoints") is None or frame.get("box") is None:
            out.append(None)
        else:
            out.append(normalise(frame["keypoints"], frame["box"]))
    return out


def missing_share(samples: Sequence[object]) -> float:
    return sum(1 for s in samples if s is None) / len(samples) if samples else 1.0


def split_for(fight: str, validation_share: float) -> Split:
    """The same split for a fight every time: a stable hash of its name."""
    bucket = int(hashlib.sha256(fight.encode()).hexdigest(), 16) % 10_000 / 10_000
    return "validation" if bucket < validation_share else "train"


def fight_windows(
    fight: str,
    split: Split,
    frames: Mapping[Corner, Sequence[Mapping[str, Any]]],
    tags: Sequence[Mapping[str, Any]],
    config: WindowsConfig,
) -> list[Window]:
    """Every window for one fight: strikes, rejected suggestions, and background."""
    windows: list[Window] = []

    def add(kind: Kind, label: str, corner: Corner, center: int, tag_id: str | None) -> bool:
        samples = cut_window(frames.get(corner, []), center, config)
        if missing_share(samples) > config.max_missing:
            return False
        windows.append(
            {
                "fight": fight,
                "split": split,
                "kind": kind,
                "label": label,
                "fighter": corner,
                "tag_id": tag_id,
                "center_ms": center,
                "samples": samples,
            }
        )
        return True

    positives: dict[Corner, int] = {"red": 0, "blue": 0}
    for tag in sorted(tags, key=lambda t: (t["timestamp_ms"], str(t["id"]))):
        corner: Corner = tag["fighter"]
        if tag["status"] == "confirmed" and tag.get("weapon"):
            if add("strike", tag["weapon"], corner, tag["timestamp_ms"], str(tag["id"])):
                positives[corner] += 1
        elif tag["status"] == "rejected":
            add("rejected", "none", corner, tag["timestamp_ms"], str(tag["id"]))

    for corner in ("red", "blue"):
        tag_times = sorted(t["timestamp_ms"] for t in tags if t["fighter"] == corner)
        wanted = round(positives[corner] * config.negatives_per_positive)
        times = background_times(
            frames.get(corner, []), tag_times, wanted, config, f"{fight}:{corner}"
        )
        for center in times:
            add("background", "none", corner, center, None)
    return windows


def background_times(
    frames: Sequence[Mapping[str, Any]],
    tag_times: Sequence[int],
    count: int,
    config: WindowsConfig,
    seed_key: str,
) -> list[int]:
    """Up to `count` frame times with keypoints, at least `negative_gap_ms` from any
    tag of this fighter, picked with a seed so a rerun gives the same windows."""
    if count <= 0:
        return []
    candidates = [
        f["timestamp_ms"]
        for f in frames
        if f.get("keypoints") is not None
        and all(abs(f["timestamp_ms"] - t) >= config.negative_gap_ms for t in tag_times)
    ]
    rng = random.Random(f"{config.seed}:{seed_key}")
    picked = rng.sample(candidates, min(count, len(candidates)))
    return sorted(picked)


def summary(windows: Sequence[Window]) -> dict[str, dict[str, int]]:
    """Window counts per split and label, for the manifest."""
    out: dict[str, dict[str, int]] = {}
    for w in windows:
        per_label = out.setdefault(w["split"], {})
        per_label[w["label"]] = per_label.get(w["label"], 0) + 1
    return {split: dict(sorted(labels.items())) for split, labels in sorted(out.items())}
