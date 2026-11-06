from pathlib import Path

import pytest

from strikelens_cv.overlay import DEFAULT_OVERLAY_CONFIG, OverlayConfig, load_overlay_config


def test_default_file_matches_the_defaults() -> None:
    assert load_overlay_config(DEFAULT_OVERLAY_CONFIG) == OverlayConfig()


def test_unknown_key_is_an_error(tmp_path: Path) -> None:
    path = tmp_path / "overlay.toml"
    path.write_text("min_visiblity = 0.5\n")
    with pytest.raises(ValueError, match="min_visiblity"):
        load_overlay_config(path)


@pytest.mark.parametrize(
    "values",
    [
        {"min_visibility": 1.5},
        {"timeline_height": 4},
        {"crf": 60},
    ],
)
def test_bad_values(values: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        OverlayConfig(**values)  # type: ignore[arg-type]
