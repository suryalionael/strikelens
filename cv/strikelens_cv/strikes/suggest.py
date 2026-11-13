"""Run strike suggestions for one fight: files in, files (and optionally the API) out."""

import json
import tomllib
import urllib.error
import urllib.request
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from strikelens_cv import __version__
from strikelens_cv.paths import CONFIG_DIR, processed_dir
from strikelens_cv.strikes.config import WindowsConfig
from strikelens_cv.strikes.infer import pick_peaks, select, suggestions
from strikelens_cv.strikes.models import StrikeModel, load_model
from strikelens_cv.strikes.windows import cut_window, missing_share

DEFAULT_INFER_CONFIG = CONFIG_DIR / "infer.toml"
SUGGESTIONS_FILE = "strike-suggestions.json"
BULK_LIMIT = 1000  # tags per request, well under the API's limit


@dataclass(frozen=True)
class InferConfig:
    model: str = "motion-baseline"
    stride_ms: int = 100
    threshold: float = 0.9
    min_gap_ms: int = 700
    merge_gap_ms: int = 1000
    max_per_round: int = 50

    def __post_init__(self) -> None:
        if self.stride_ms <= 0:
            raise ValueError("stride_ms must be above 0")
        if not 0 < self.threshold < 1:
            raise ValueError("threshold must be between 0 and 1")
        if self.min_gap_ms < 0:
            raise ValueError("min_gap_ms must be at least 0")
        if self.merge_gap_ms < 0:
            raise ValueError("merge_gap_ms must be at least 0")
        if self.max_per_round < 1:
            raise ValueError("max_per_round must be at least 1")


def load_infer_config(path: Path = DEFAULT_INFER_CONFIG) -> InferConfig:
    with path.open("rb") as handle:
        raw = tomllib.load(handle)
    unknown = sorted(set(raw) - set(InferConfig.__dataclass_fields__))
    if unknown:
        raise ValueError(f"unknown inference settings in {path.name}: {', '.join(unknown)}")
    return InferConfig(**raw)


@dataclass(frozen=True)
class SuggestResult:
    path: Path
    tags: list[dict[str, Any]]
    posted: int | None
    replaced: int = 0


def _read(path: Path, hint: str) -> Any:
    if not path.is_file():
        raise FileNotFoundError(f"{path} not found; {hint}")
    return json.loads(path.read_text())


def score_corner(
    frames: list[dict[str, Any]],
    rounds: list[dict[str, Any]],
    model: StrikeModel,
    windows: WindowsConfig,
    config: InferConfig,
) -> tuple[list[int], list[float], list[str | None]]:
    """A score every `stride_ms` inside the marked rounds. Windows with too many
    missing samples score 0, so a gap in the keypoints is never a peak."""
    times = [
        t for r in rounds for t in range(int(r["start_ms"]), int(r["end_ms"]) + 1, config.stride_ms)
    ]
    cut = [cut_window(frames, t, windows) for t in times]
    usable = [i for i, w in enumerate(cut) if missing_share(w) <= windows.max_missing]
    sample_ms = (windows.before_ms + windows.after_ms) / (windows.samples - 1)
    predictions = model.predict([cut[i] for i in usable], sample_ms)
    scores = [0.0] * len(times)
    weapons: list[str | None] = [None] * len(times)
    for i, p in zip(usable, predictions, strict=True):
        scores[i], weapons[i] = p["strike"], p["weapon"]
    return times, scores, weapons


def _call(request: urllib.request.Request) -> Any:
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read()
    except urllib.error.HTTPError as error:
        detail = error.read().decode(errors="replace")
        raise ValueError(f"the API refused the request ({error.code}): {detail[:300]}") from error
    return json.loads(body) if body else None


def fight_tags(api_url: str, fight_id: str) -> list[dict[str, Any]]:
    """Every tag the API holds for the fight."""
    tags: list[dict[str, Any]] = _call(
        urllib.request.Request(f"{api_url.rstrip('/')}/fights/{fight_id}/tags")
    )
    return tags


def delete_tags(api_url: str, fight_id: str, tag_ids: Sequence[str]) -> int:
    """Delete tags one by one. Returns how many were deleted."""
    for tag_id in tag_ids:
        _call(
            urllib.request.Request(
                f"{api_url.rstrip('/')}/fights/{fight_id}/tags/{tag_id}", method="DELETE"
            )
        )
    return len(tag_ids)


def replaceable(tags: Sequence[Mapping[str, Any]], created_by: str) -> list[str]:
    """IDs of this model's suggestions nobody has reviewed yet. Pure."""
    return [
        str(t["id"])
        for t in tags
        if t["source"] == "cv" and t["status"] == "pending" and t["created_by"] == created_by
    ]


def post_tags(api_url: str, fight_id: str, tags: list[dict[str, Any]]) -> int:
    """POST the tags to the API's bulk endpoint, in chunks. Returns how many were saved."""
    saved = 0
    for start in range(0, len(tags), BULK_LIMIT):
        # The API takes the fight from the URL and refuses it in the body.
        chunk = [
            {k: v for k, v in tag.items() if k != "fight_id"}
            for tag in tags[start : start + BULK_LIMIT]
        ]
        request = urllib.request.Request(
            f"{api_url.rstrip('/')}/fights/{fight_id}/tags/bulk",
            data=json.dumps(chunk).encode(),
            headers={"content-type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                saved += len(json.loads(response.read()))
        except urllib.error.HTTPError as error:
            detail = error.read().decode(errors="replace")
            if error.code == 409:
                raise ValueError(
                    "the API already has some of these suggestions (same model, same fight). "
                    "Reject or delete them first, or change the settings."
                ) from error
            raise ValueError(
                f"the API refused the suggestions ({error.code}): {detail[:300]}"
            ) from error
    return saved


def suggest_strikes(
    fight: str,
    windows: WindowsConfig,
    config: InferConfig,
    api_url: str | None = None,
    replace: bool = False,
) -> SuggestResult:
    """Score both fighters, pick peaks, keep one per moment and a budget per round
    (`select`), and write strike-suggestions.json. With `api_url`, also post them to
    the fight in the API as pending tags, next to no tag already there. With
    `replace`, this model's unreviewed suggestions are deleted first."""
    if replace and not api_url:
        raise ValueError("--replace needs --post: it replaces suggestions in the API")
    out_dir = processed_dir(fight)
    fight_data = _read(
        out_dir / "fight.json",
        "save the fight from the API: curl -s http://localhost:8000/fights/<id> > fight.json",
    )
    if not fight_data.get("rounds"):
        raise ValueError("fight.json has no rounds; mark them in the tagger and save it again")
    model = load_model(config.model)
    peaks = {}
    for corner in ("red", "blue"):
        data = _read(out_dir / "keypoints" / f"{corner}.json", "run strikelens-cv pose first")
        frames = sorted(data["frames"], key=lambda f: f["timestamp_ms"])
        times, scores, weapons = score_corner(frames, fight_data["rounds"], model, windows, config)
        peaks[corner] = pick_peaks(times, scores, weapons, config.threshold, config.min_gap_ms)
    created_by = f"{model.name}@{model.version}"
    fight_id = str(fight_data["id"])
    existing = fight_tags(api_url, fight_id) if api_url else []
    stale = replaceable(existing, created_by) if replace else []
    if stale and api_url:
        delete_tags(api_url, fight_id, stale)
    # Tags already in the fight keep their place: no new suggestion lands next to them.
    # Suggestions still waiting for review also use up their round's budget.
    kept = [t for t in existing if str(t["id"]) not in set(stale)]
    waiting: dict[int, int] = {}
    for t in kept:
        if t["status"] == "pending" and t.get("round") is not None:
            waiting[int(t["round"])] = waiting.get(int(t["round"]), 0) + 1
    tags = select(
        suggestions(fight_data, peaks, created_by),
        config.max_per_round,
        config.merge_gap_ms,
        [int(t["timestamp_ms"]) for t in kept],
        waiting,
    )
    path = out_dir / SUGGESTIONS_FILE
    path.write_text(
        json.dumps(
            {
                "strikelens_cv": __version__,
                "model": created_by,
                "config": asdict(config),
                "windows": windows.as_dict(),
                "tags": tags,
            },
            indent=2,
        )
        + "\n"
    )
    posted = post_tags(api_url, fight_id, tags) if api_url and tags else None
    return SuggestResult(path=path, tags=tags, posted=posted, replaced=len(stale))
