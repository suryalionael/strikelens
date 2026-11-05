from pathlib import Path

import pytest

from strikelens_cv.track import (
    DEFAULT_TRACK_CONFIG,
    TrackConfig,
    load_corrections,
    load_track_config,
    parse_corrections,
)


def test_default_file_matches_the_defaults() -> None:
    assert load_track_config(DEFAULT_TRACK_CONFIG) == TrackConfig()


def test_unknown_key_is_an_error(tmp_path: Path) -> None:
    path = tmp_path / "track.toml"
    path.write_text('weight = "x.pt"\n')
    with pytest.raises(ValueError, match="weight"):
        load_track_config(path)


@pytest.mark.parametrize(
    "values",
    [
        {"weights": "../yolo.pt"},
        {"weights": ""},
        {"confidence": 1.5},
        {"image_size": 0},
        {"min_track_frames": 0},
        {"max_feature_distance": 0},
    ],
)
def test_bad_values(values: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        TrackConfig(**values)  # type: ignore[arg-type]


def test_corrections_parse() -> None:
    data = {
        "corrections": [
            {"shot": 0, "track_id": 2, "corner": "red"},
            {"shot": 3, "track_id": 1, "corner": "none"},
            {"shot": 0, "track_id": 2, "corner": "blue"},  # the later entry wins
        ]
    }
    assert parse_corrections(data) == {(0, 2): "blue", (3, 1): "none"}


@pytest.mark.parametrize(
    "bad",
    [
        {},
        {"corrections": [{"shot": 0, "track_id": 1, "corner": "green"}]},
        {"corrections": [{"track_id": 1, "corner": "red"}]},
        {"corrections": [{"shot": 0, "track_id": True, "corner": "red"}]},
        {"corrections": ["red"]},
    ],
    ids=["no-list", "bad-corner", "no-shot", "bool-id", "not-object"],
)
def test_corrections_rejected(bad: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        parse_corrections(bad)


def test_load_corrections(tmp_path: Path) -> None:
    path = tmp_path / "track-corrections.json"
    path.write_text('{"corrections": [{"shot": 1, "track_id": 4, "corner": "red"}]}')
    assert load_corrections(path) == {(1, 4): "red"}
