"""Find the broadcast scoreboard in sampled frames. Needs the `ingest` extra.

No template is stored: Byon's graphics are not ours to commit. Within the
configured region, the patch that looks the same in the most frames is taken as
the scoreboard, since live video behind it keeps changing and the logo does not.
"""

from collections.abc import Sequence
from pathlib import Path
from typing import Any

from strikelens_cv.rounds.config import RoundsConfig
from strikelens_cv.rounds.core import Sample

PATCH = 12  # pixels per grid cell after shrinking the region
MAX_CANDIDATES = 600  # frames compared pairwise to find the scoreboard patch
MIN_SHARE = 0.05  # the scoreboard must be on screen in at least this share of samples
MIN_TEXTURE = 15.0  # a flat patch (plain black, sky) is not a logo


def _region(image: Any, config: RoundsConfig) -> Any:
    import cv2

    h, w = image.shape[:2]
    x1, y1, x2, y2 = config.scoreboard_region
    crop = image[int(h * y1) : int(h * y2), int(w * x1) : int(w * x2)]
    gx, gy = config.grid
    return cv2.resize(crop, (gx * PATCH, gy * PATCH), interpolation=cv2.INTER_AREA)


def _normalise(patches: Any) -> Any:
    import numpy as np

    centred = patches - patches.mean(axis=1, keepdims=True)
    return centred / (np.linalg.norm(centred, axis=1, keepdims=True) + 1e-6)


def scoreboard_samples(
    frames_dir: Path, frames: Sequence[dict[str, Any]], config: RoundsConfig
) -> list[Sample]:
    """(timestamp_ms, on screen) for one frame per `sample_ms`. All False when no
    patch repeats often enough to be a scoreboard."""
    try:
        import cv2
        import numpy as np
    except ImportError as error:
        raise RuntimeError(
            "Round suggestions need the ingest extra: cd cv && uv sync --extra ingest"
        ) from error

    picked: list[dict[str, Any]] = []
    for frame in frames:
        if not picked or frame["timestamp_ms"] - picked[-1]["timestamp_ms"] >= config.sample_ms:
            picked.append(frame)
    if not picked:
        return []
    regions = []
    for frame in picked:
        image = cv2.imread(str(frames_dir / frame["file"]), cv2.IMREAD_GRAYSCALE)
        if image is None:
            raise FileNotFoundError(f"cannot read frame {frame['file']}")
        regions.append(_region(image, config).astype(np.float32))
    stack = np.stack(regions)
    n = len(stack)
    candidates = np.linspace(0, n - 1, min(n, MAX_CANDIDATES)).astype(int)

    best: tuple[int, Any] | None = None  # (matches, similarity of every sample)
    gx, gy = config.grid
    for row in range(gy):
        for col in range(gx):
            cells = stack[:, row * PATCH : (row + 1) * PATCH, col * PATCH : (col + 1) * PATCH]
            flat = cells.reshape(n, -1)
            unit = _normalise(flat)
            pair = unit[candidates] @ unit[candidates].T
            counts = (pair > config.match).sum(axis=1)
            medoid = int(candidates[int(counts.argmax())])
            if flat[medoid].std() < MIN_TEXTURE:
                continue
            similarity = unit @ unit[medoid]
            matches = int((similarity > config.match).sum())
            if best is None or matches > best[0]:
                best = (matches, similarity)

    if best is None or best[0] < MIN_SHARE * n:
        return [(f["timestamp_ms"], False) for f in picked]
    similarity = best[1]
    return [
        (f["timestamp_ms"], bool(s > config.match)) for f, s in zip(picked, similarity, strict=True)
    ]
