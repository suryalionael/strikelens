"""Where pipeline output goes. Everything lands under the gitignored data/ folder."""

import os
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = REPO_ROOT / "cv" / "configs"


def data_dir() -> Path:
    """The data/ folder, or STRIKELENS_DATA_DIR when set (tests use a temp folder)."""
    return Path(os.environ.get("STRIKELENS_DATA_DIR", REPO_ROOT / "data"))


def models_dir() -> Path:
    """The models/ folder for local weights, or STRIKELENS_MODELS_DIR when set."""
    return Path(os.environ.get("STRIKELENS_MODELS_DIR", REPO_ROOT / "models"))


def fight_slug(name: str) -> str:
    """A safe folder name for a fight, for example "Byon 40 / Main" -> "byon-40-main"."""
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    if not slug:
        raise ValueError("fight name must contain at least one letter or digit")
    return slug


def processed_dir(fight: str) -> Path:
    return data_dir() / "processed" / fight_slug(fight)
