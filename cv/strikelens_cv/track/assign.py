"""Turn short ByteTrack IDs into two stable fighters, red and blue.

ByteTrack IDs only last within a shot: a camera cut starts new IDs. So within each
shot we pick at most two fighters (each may be several track fragments), and across
shots we match them to red and blue by how their shorts look (a colour histogram).

All functions here are pure: plain lists and dicts in, plain lists and dicts out.
"""

from collections import defaultdict
from collections.abc import Callable, Iterable, Sequence
from itertools import permutations
from typing import Literal, NotRequired, TypedDict

from strikelens_cv.track.config import TrackConfig
from strikelens_cv.track.corrections import Corner, Corrections

CORNERS: tuple[Corner, ...] = ("red", "blue")

Box = list[float]  # [x1, y1, x2, y2] in pixels
SeededBy = Literal["corrections", "left_is_red", "none"]


class Detection(TypedDict):
    frame: int
    shot: int
    track_id: int
    box: Box
    confidence: float
    feature: list[float]
    # Share of skin on the chest, for the referee filter. Missing before #20.
    torso_skin: NotRequired[float | None]
    # Share of dark (black, not skin) pixels on the chest. Missing before the dark rule.
    torso_dark: NotRequired[float | None]


class FrameInfo(TypedDict):
    index: int
    timestamp_ms: int
    shot: int
    skipped: bool


class TrackSummary(TypedDict):
    shot: int
    track_id: int
    first_frame: int
    last_frame: int
    frames: int
    mean_area: float
    mean_x: float
    feature: list[float]
    torso_skin: float | None
    torso_dark: float | None


class Fighter(TypedDict):
    track_ids: list[int]
    frames: int
    mean_x: float
    feature: list[float]
    corner: Corner | None  # set only by a correction


class ShotResult(TypedDict):
    shot: int
    red: list[int]
    blue: list[int]
    dropped: list[int]
    uncertain: bool


class Assignment(TypedDict):
    seeded_by: SeededBy
    shots: list[ShotResult]


class TrackFrame(TypedDict):
    index: int
    timestamp_ms: int
    red: Box | None
    blue: Box | None


# Small helpers


def _area(box: Box) -> float:
    return max(0.0, box[2] - box[0]) * max(0.0, box[3] - box[1])


def _weighted_mean(vectors: Sequence[Sequence[float]], weights: Sequence[float]) -> list[float]:
    total = sum(weights)
    if not vectors or total == 0:
        return []
    return [
        sum(v[i] * w for v, w in zip(vectors, weights, strict=True)) / total
        for i in range(len(vectors[0]))
    ]


def feature_distance(a: Sequence[float], b: Sequence[float]) -> float:
    """Total variation distance between two normalised histograms: 0 same, 1 disjoint."""
    if len(a) != len(b):
        raise ValueError("features must have the same length")
    return sum(abs(x - y) for x, y in zip(a, b, strict=True)) / 2


def _overlaps(a: tuple[int, int], b: tuple[int, int]) -> bool:
    return a[0] <= b[1] and b[0] <= a[1]


# Steps


def summarise_tracks(detections: Iterable[Detection]) -> list[TrackSummary]:
    """One summary per (shot, track): when it is seen, how big, where, and how it looks."""
    grouped: dict[tuple[int, int], list[Detection]] = defaultdict(list)
    for d in detections:
        grouped[(d["shot"], d["track_id"])].append(d)
    summaries: list[TrackSummary] = []
    for (shot, track_id), items in sorted(grouped.items()):
        areas = [_area(d["box"]) for d in items]
        skins = [s for d in items if (s := d.get("torso_skin")) is not None]
        darks = [s for d in items if (s := d.get("torso_dark")) is not None]
        summaries.append(
            {
                "shot": shot,
                "track_id": track_id,
                "first_frame": min(d["frame"] for d in items),
                "last_frame": max(d["frame"] for d in items),
                "frames": len(items),
                "mean_area": sum(areas) / len(items),
                "mean_x": sum((d["box"][0] + d["box"][2]) / 2 for d in items) / len(items),
                "feature": _weighted_mean([d["feature"] for d in items], [1.0] * len(items)),
                "torso_skin": sum(skins) / len(skins) if skins else None,
                "torso_dark": sum(darks) / len(darks) if darks else None,
            }
        )
    return summaries


def _fighter(tracks: Sequence[TrackSummary], corner: Corner | None) -> Fighter:
    weights = [float(t["frames"]) for t in tracks]
    return {
        "track_ids": sorted(t["track_id"] for t in tracks),
        "frames": sum(t["frames"] for t in tracks),
        "mean_x": sum(t["mean_x"] * t["frames"] for t in tracks) / sum(weights),
        "feature": _weighted_mean([t["feature"] for t in tracks], weights),
        "corner": corner,
    }


def pick_fighters(
    tracks: Sequence[TrackSummary],
    config: TrackConfig,
    corrections: Corrections | None = None,
    is_excluded: Callable[[TrackSummary], bool] | None = None,
) -> tuple[list[Fighter], list[int]]:
    """At most two fighters in one shot, and the track IDs left out.

    Corrections come first: "none" drops a track, "red" or "blue" pins it. Then the
    strongest remaining tracks (frames seen x mean box size) are added. A track that
    never overlaps a fighter in time is taken as a fragment of that fighter (ByteTrack
    often starts a new ID mid-shot). A track that overlaps both fighters is a third
    person, often the referee, and is dropped. `is_excluded` is where the referee
    filter (#20) plugs in.
    """
    corrections = corrections or {}
    dropped: list[int] = []
    pinned: dict[Corner, list[TrackSummary]] = {"red": [], "blue": []}
    free: list[TrackSummary] = []
    for t in tracks:
        corner = corrections.get((t["shot"], t["track_id"]))
        if corner == "none":
            dropped.append(t["track_id"])
        elif corner in CORNERS:
            pinned[corner].append(t)
        elif t["frames"] < config.min_track_frames or (is_excluded and is_excluded(t)):
            dropped.append(t["track_id"])
        else:
            free.append(t)

    groups: list[tuple[Corner | None, list[TrackSummary]]] = [
        (corner, members) for corner, members in pinned.items() if members
    ]
    for t in sorted(free, key=lambda t: t["frames"] * t["mean_area"], reverse=True):
        span = (t["first_frame"], t["last_frame"])
        fits = [
            g
            for g in groups
            if not any(_overlaps(span, (m["first_frame"], m["last_frame"])) for m in g[1])
        ]
        if fits:
            # Join the fragment to the fighter it looks most like.
            best = min(
                fits, key=lambda g: feature_distance(t["feature"], _fighter(g[1], None)["feature"])
            )
            best[1].append(t)
        elif len(groups) < 2:
            groups.append((None, [t]))
        else:
            dropped.append(t["track_id"])

    return [_fighter(members, corner) for corner, members in groups], sorted(dropped)


def _update(ref: list[float] | None, weight: float, fighter: Fighter) -> tuple[list[float], float]:
    if ref is None:
        return list(fighter["feature"]), float(fighter["frames"])
    new = _weighted_mean([ref, fighter["feature"]], [weight, float(fighter["frames"])])
    return new, weight + fighter["frames"]


def assign_corners(
    summaries: Sequence[TrackSummary],
    config: TrackConfig,
    corrections: Corrections | None = None,
    is_excluded: Callable[[TrackSummary], bool] | None = None,
) -> Assignment:
    """Red and blue track IDs for every shot, in shot order.

    Each corner keeps a reference look (running mean of its fighters' features).
    Corrections pin tracks and seed the references. With no correction before the
    first shot that shows two fighters, the left one is taken as red. That is a
    provisional guess, reported as `seeded_by: "left_is_red"`, for the analyst to
    check and correct.
    """
    by_shot: dict[int, list[TrackSummary]] = defaultdict(list)
    for s in summaries:
        by_shot[s["shot"]].append(s)

    refs: dict[Corner, list[float] | None] = {"red": None, "blue": None}
    weights: dict[Corner, float] = {"red": 0.0, "blue": 0.0}
    seeded_by: SeededBy = "none"
    results: list[ShotResult] = []

    for shot in sorted(by_shot):
        fighters, dropped = pick_fighters(by_shot[shot], config, corrections, is_excluded)
        chosen: dict[Corner, Fighter] = {f["corner"]: f for f in fighters if f["corner"]}
        if chosen and seeded_by == "none":
            seeded_by = "corrections"
        free = [f for f in fighters if f["corner"] is None]
        open_corners = [c for c in CORNERS if c not in chosen]
        uncertain = False

        if free and refs["red"] is None and refs["blue"] is None and not chosen:
            if len(free) == 2:
                left, right = sorted(free, key=lambda f: f["mean_x"])
                chosen = {"red": left, "blue": right}
                seeded_by = "left_is_red"
            else:
                # One fighter and nothing to compare with: leave the shot unassigned.
                uncertain = True
                dropped = sorted(dropped + free[0]["track_ids"])
        elif free:
            best_cost, best = float("inf"), None
            for corners in permutations(open_corners, len(free)):
                cost = 0.0
                for f, c in zip(free, corners, strict=True):
                    ref = refs[c]
                    cost += (
                        config.max_feature_distance
                        if ref is None
                        else feature_distance(f["feature"], ref)
                    )
                if cost < best_cost:
                    best_cost, best = cost, corners
            if best is not None:
                chosen.update(dict(zip(best, free, strict=True)))
                uncertain = best_cost / len(free) > config.max_feature_distance

        for corner, fighter in chosen.items():
            # An uncertain match is still reported, but it must not teach the references.
            if fighter["corner"] is not None or not uncertain:
                refs[corner], weights[corner] = _update(refs[corner], weights[corner], fighter)

        results.append(
            {
                "shot": shot,
                "red": chosen["red"]["track_ids"] if "red" in chosen else [],
                "blue": chosen["blue"]["track_ids"] if "blue" in chosen else [],
                "dropped": dropped,
                "uncertain": uncertain,
            }
        )
    return {"seeded_by": seeded_by, "shots": results}


def build_tracks(
    frames: Sequence[FrameInfo], detections: Iterable[Detection], assignment: Assignment
) -> list[TrackFrame]:
    """One entry per frame with the red and blue box, or null when not seen.

    Skipped frames (inside replays and non-fight segments) and unassigned shots
    come out with both boxes null. If a corner has two boxes in one frame, the more
    confident one wins.
    """
    owner: dict[tuple[int, int], Corner] = {}
    for result in assignment["shots"]:
        for corner in CORNERS:
            for track_id in result[corner]:
                owner[(result["shot"], track_id)] = corner

    best: dict[tuple[int, Corner], Detection] = {}
    for d in detections:
        corner = owner.get((d["shot"], d["track_id"]))
        if corner is None:
            continue
        key = (d["frame"], corner)
        if key not in best or d["confidence"] > best[key]["confidence"]:
            best[key] = d

    out: list[TrackFrame] = []
    for f in frames:
        red = None if f["skipped"] else best.get((f["index"], "red"))
        blue = None if f["skipped"] else best.get((f["index"], "blue"))
        out.append(
            {
                "index": f["index"],
                "timestamp_ms": f["timestamp_ms"],
                "red": red["box"] if red else None,
                "blue": blue["box"] if blue else None,
            }
        )
    return out
