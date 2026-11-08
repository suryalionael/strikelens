"""The scoreboard detector on synthetic frames: noise with a fixed logo in some.

Skips without the ingest extra (OpenCV and numpy), so it never runs in CI.
"""

from pathlib import Path

import pytest

from strikelens_cv.rounds import RoundsConfig, suggest_rounds
from strikelens_cv.rounds.detect import scoreboard_samples

cv2 = pytest.importorskip("cv2")
np = pytest.importorskip("numpy")

W, H = 320, 180


def write_frames(folder: Path, on: range, count: int = 120) -> list[dict[str, object]]:
    """One frame a second. A textured "logo" sits bottom left while `on`."""
    rng = np.random.default_rng(7)
    # Large blocks, like the letters and panels of a real graphic. Pixel noise
    # would average out to flat grey when the region is shrunk.
    blocks = rng.integers(0, 2, (3, 6), dtype=np.uint8) * 255
    logo = np.repeat(np.kron(blocks, np.ones((8, 8), dtype=np.uint8))[:, :, None], 3, axis=2)
    frames = []
    for i in range(count):
        image = rng.integers(0, 255, (H, W, 3), dtype=np.uint8)  # live video: always new
        if i in on:
            image[130:154, 20:68] = logo
        name = f"{i:06}.jpg"
        cv2.imwrite(str(folder / name), image)
        frames.append({"index": i, "file": name, "timestamp_ms": i * 1000})
    return frames


def test_finds_the_scoreboard_when_it_is_on_screen(tmp_path: Path) -> None:
    frames = write_frames(tmp_path, on=range(30, 90))
    samples = scoreboard_samples(tmp_path, frames, RoundsConfig())
    on = [t // 1000 for t, shown in samples if shown]
    assert on == list(range(30, 90))


def test_no_scoreboard_means_no_samples_on(tmp_path: Path) -> None:
    frames = write_frames(tmp_path, on=range(0))
    assert not any(shown for _, shown in scoreboard_samples(tmp_path, frames, RoundsConfig()))


def test_detected_samples_become_a_round(tmp_path: Path) -> None:
    frames = write_frames(tmp_path, on=range(30, 90))
    samples = scoreboard_samples(tmp_path, frames, RoundsConfig())
    [round_] = suggest_rounds(samples, 120_000, RoundsConfig())
    assert (round_["start_ms"], round_["end_ms"], round_["partial"]) == (30_000, 89_000, True)
