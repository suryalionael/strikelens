from pathlib import Path

import pytest


@pytest.fixture
def data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point all pipeline output at a temporary folder, never the real data/."""
    root = tmp_path / "data"
    monkeypatch.setenv("STRIKELENS_DATA_DIR", str(root))
    return root
