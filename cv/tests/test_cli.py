from pathlib import Path

import pytest

from strikelens_cv import __version__
from strikelens_cv.cli import main


def test_version_flag_prints_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert capsys.readouterr().out.strip() == f"strikelens-cv {__version__}"


def test_no_args_prints_help(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([]) == 0
    assert "strikelens-cv" in capsys.readouterr().out


def test_ingest_reports_a_missing_video(
    tmp_path: Path, data_dir: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["ingest", str(tmp_path / "nope.mp4"), "--fight", "x"]) == 1
    assert "video not found" in capsys.readouterr().err


def test_ingest_needs_a_fight_name(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["ingest", "fight.mp4"])
    assert exc.value.code == 2
    assert "--fight" in capsys.readouterr().err
