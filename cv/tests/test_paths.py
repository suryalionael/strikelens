from pathlib import Path

import pytest

from strikelens_cv import paths


def test_default_data_dir_is_the_gitignored_repo_folder(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("STRIKELENS_DATA_DIR", raising=False)
    assert paths.data_dir() == paths.REPO_ROOT / "data"


def test_data_dir_can_be_overridden(data_dir: Path) -> None:
    assert paths.data_dir() == data_dir
    assert paths.processed_dir("Fight 1") == data_dir / "processed" / "fight-1"


@pytest.mark.parametrize(
    ("name", "slug"),
    [("Byon 40 / Main Event", "byon-40-main-event"), ("  red_vs_blue ", "red-vs-blue")],
)
def test_fight_slug(name: str, slug: str) -> None:
    assert paths.fight_slug(name) == slug


def test_fight_slug_rejects_names_with_no_letters() -> None:
    with pytest.raises(ValueError):
        paths.fight_slug("///")


def test_fight_slug_cannot_escape_the_data_folder() -> None:
    assert paths.fight_slug("../../etc") == "etc"
