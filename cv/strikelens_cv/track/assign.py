"""Turn short ByteTrack IDs into two stable fighters, red and blue.

ByteTrack IDs only last within a shot: a camera cut starts new IDs. So within each
shot we pick at most two fighters (each may be several track fragments), and across
shots we match them to red and blue: by their kit colour where it is clear (red or
blue singlets, kit.py), otherwise by how their shorts look (a colour histogram).

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
SeededBy = Literal["corrections", "kit", "left_is_red", "none"]
KitShare = Literal["torso_red", "torso_blue"]


class Detection(TypedDict):
    frame: int
    shot: int
    track_id: int
    box: Box
    confidence: float
    feature: list[float]
    # Share of skin on the chest, for the referee filter. Missing before #20.
    torso_skin: NotRequired[float | None]
    # ByteTrack's own ID, before split.py cut tracks that switch person (#64).
    bytetrack_id: NotRequired[int]
    # Share of dark (black, not skin) pixels on the chest. Missing before the dark rule.
    torso_dark: NotRequired[float | None]
    # Shares of red and blue kit pixels on the chest. Missing before kit colour.
    torso_red: NotRequired[float | None]
    torso_blue: NotRequired[float | None]


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
    torso_red: float | None
    torso_blue: float | None


class Fighter(TypedDict):
    track_ids: list[int]
    frames: int
    mean_x: float
    feature: list[float]
    corner: Corner | None  # set only by a correction
    kit_red: float | None
    kit_blue: float | None
    # Set when the fighter was built from tracks whose own kit is clearly this
    # corner. The fighter's mean kit can be diluted by fragments without kit.
    kit: NotRequired[Corner | None]


class ShotResult(TypedDict):
    shot: int
    red: list[int]
    blue: list[int]
    dropped: list[int]
    uncertain: bool
    by_kit: bool  # the kit colour decided at least one corner


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
        reds = [s for d in items if (s := d.get("torso_red")) is not None]
        blues = [s for d in items if (s := d.get("torso_blue")) is not None]
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
                "torso_red": sum(reds) / len(reds) if reds else None,
                "torso_blue": sum(blues) / len(blues) if blues else None,
            }
        )
    return summaries


def _kit_mean(tracks: Sequence[TrackSummary], key: KitShare) -> float | None:
    """Frame-weighted mean of a kit share over the tracks that have one."""
    pairs = [(share, t["frames"]) for t in tracks if (share := t[key]) is not None]
    total = sum(frames for _, frames in pairs)
    return sum(share * frames for share, frames in pairs) / total if total else None


def _fighter(
    tracks: Sequence[TrackSummary], corner: Corner | None, kit: Corner | None = None
) -> Fighter:
    weights = [float(t["frames"]) for t in tracks]
    return {
        "kit": kit,
        "track_ids": sorted(t["track_id"] for t in tracks),
        "frames": sum(t["frames"] for t in tracks),
        "mean_x": sum(t["mean_x"] * t["frames"] for t in tracks) / sum(weights),
        "feature": _weighted_mean([t["feature"] for t in tracks], weights),
        "corner": corner,
        "kit_red": _kit_mean(tracks, "torso_red"),
        "kit_blue": _kit_mean(tracks, "torso_blue"),
    }


def fighter_kit(fighter: Fighter, config: TrackConfig) -> Corner | None:
    """The corner a fighter's kit says, or None when it is not clearly red or blue."""
    return fighter.get("kit") or _kit_says(fighter["kit_red"], fighter["kit_blue"], config)


def track_kit(track: TrackSummary, config: TrackConfig) -> Corner | None:
    """The corner one track's own kit says. None when the kit is off or unclear."""
    if not config.kit_corner:
        return None
    return _kit_says(track["torso_red"], track["torso_blue"], config)


def _kit_says(red: float | None, blue: float | None, config: TrackConfig) -> Corner | None:
    if red is None or blue is None:
        return None
    if red - blue >= config.min_kit_share:
        return "red"
    if blue - red >= config.min_kit_share:
        return "blue"
    return None


def _kit_trusted(
    free: Sequence[TrackSummary], pinned: dict[Corner, list[TrackSummary]], config: TrackConfig
) -> bool:
    """Whether the kit can be trusted in this shot at all.

    Not when a correction pins a track to the corner its own kit contradicts, and
    not when two people in the same kit are on screen together while nobody wears
    the other corner's kit (an event where the kit does not match the corner).
    """
    for corner, members in pinned.items():
        if any((kit := track_kit(t, config)) is not None and kit != corner for t in members):
            return False
    by_kit: dict[Corner, list[TrackSummary]] = {"red": [], "blue": []}
    for t in free:
        if (kit := track_kit(t, config)) is not None:
            by_kit[kit].append(t)
    for corner, other in (("red", "blue"), ("blue", "red")):
        same = by_kit[corner]
        together = any(
            _overlaps((a["first_frame"], a["last_frame"]), (b["first_frame"], b["last_frame"]))
            for i, a in enumerate(same)
            for b in same[i + 1 :]
        )
        if together and not by_kit[other]:
            return False
    return True


def pick_fighters(
    tracks: Sequence[TrackSummary],
    config: TrackConfig,
    corrections: Corrections | None = None,
    is_excluded: Callable[[TrackSummary], bool] | None = None,
) -> tuple[list[Fighter], list[int]]:
    """At most two fighters in one shot, and the track IDs left out.

    Corrections come first: "none" drops a track, "red" or "blue" pins it. Tracks
    seen too briefly, excluded by the referee filter (`is_excluded`), or much
    smaller than the biggest track in the shot (`min_fighter_area`, which keeps
    out the crowd behind the ropes) are dropped.

    Then the kit: a track whose own chest is clearly red or blue joins that
    corner, even when it overlaps other tracks of the same corner in time
    (`build_tracks` keeps one box per corner per frame).

    The rest are added strongest first (frames seen x mean box size). A track that
    never overlaps a fighter in time is taken as a fragment of that fighter
    (ByteTrack often starts a new ID mid-shot), unless its kit says the other
    corner. A track that overlaps both fighters is a third person and is dropped.
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

    # Measured against every track seen long enough, the referee included: he is
    # fighter-sized, and a shot where the filter drops him must not make the crowd
    # look big by comparison.
    biggest = max(
        (t["mean_area"] for t in tracks if t["frames"] >= config.min_track_frames), default=0
    )
    small = [t for t in free if t["mean_area"] < config.min_fighter_area * biggest]
    dropped += [t["track_id"] for t in small]
    free = [t for t in free if t not in small]

    kit_tracks: dict[Corner, list[TrackSummary]] = {"red": [], "blue": []}
    if _kit_trusted(free, pinned, config):
        for t in free:
            corner = track_kit(t, config)
            # A corner a correction holds is left to the correction.
            if corner is not None and not pinned[corner]:
                kit_tracks[corner].append(t)
        free = [t for t in free if not any(t in members for members in kit_tracks.values())]

    # (corner from a correction, corner from the kit, members)
    groups: list[tuple[Corner | None, Corner | None, list[TrackSummary]]] = [
        (corner, None, members) for corner, members in pinned.items() if members
    ] + [(None, corner, members) for corner, members in kit_tracks.items() if members]
    for t in sorted(free, key=lambda t: t["frames"] * t["mean_area"], reverse=True):
        span = (t["first_frame"], t["last_frame"])
        fits = [
            g
            for g in groups
            if not any(_overlaps(span, (m["first_frame"], m["last_frame"])) for m in g[2])
        ]
        if fits:
            # Join the fragment to the fighter it looks most like.
            best = min(
                fits, key=lambda g: feature_distance(t["feature"], _fighter(g[2], None)["feature"])
            )
            best[2].append(t)
        elif len(groups) < 2:
            groups.append((None, None, [t]))
        else:
            dropped.append(t["track_id"])

    fighters = [_fighter(members, corner, kit) for corner, kit, members in groups]
    return fighters, sorted(dropped)


def _update(ref: list[float] | None, weight: float, fighter: Fighter) -> tuple[list[float], float]:
    if ref is None:
        return list(fighter["feature"]), float(fighter["frames"])
    new = _weighted_mean([ref, fighter["feature"]], [weight, float(fighter["frames"])])
    return new, weight + fighter["frames"]


def _kit_claims(
    free: Sequence[Fighter], taken: Iterable[Corner], config: TrackConfig
) -> dict[Corner, Fighter]:
    """Corners the kit colour settles in one shot. Empty when the kit is off or unclear.

    If two fighters claim the same corner, or a correction already holds it, the
    kit is not trusted for this shot at all.
    """
    if not config.kit_corner:
        return {}
    claims = [(c, f) for f in free if (c := fighter_kit(f, config)) is not None]
    corners = [c for c, _ in claims]
    if len(set(corners)) < len(corners) or set(corners) & set(taken):
        return {}
    return dict(claims)


def assign_corners(
    summaries: Sequence[TrackSummary],
    config: TrackConfig,
    corrections: Corrections | None = None,
    is_excluded: Callable[[TrackSummary], bool] | None = None,
) -> Assignment:
    """Red and blue track IDs for every shot, in shot order.

    Trust goes corrections, then kit colour, then the shorts histogram. Each
    corner keeps a reference look (running mean of its fighters' features).
    Corrections pin tracks, and a fighter in clearly red or blue kit takes that
    corner; both teach the references. Other fighters are matched to the
    references. With nothing to go on before the first shot that shows two
    fighters, the left one is taken as red. That is a provisional guess, reported
    as `seeded_by: "left_is_red"`, for the analyst to check and correct.
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
        by_kit = _kit_claims(free, chosen, config)
        if by_kit:
            chosen.update(by_kit)
            free = [f for f in free if not any(f is k for k in by_kit.values())]
            if seeded_by == "none":
                seeded_by = "kit"
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
            if fighter["corner"] is not None or corner in by_kit or not uncertain:
                refs[corner], weights[corner] = _update(refs[corner], weights[corner], fighter)

        results.append(
            {
                "shot": shot,
                "red": chosen["red"]["track_ids"] if "red" in chosen else [],
                "blue": chosen["blue"]["track_ids"] if "blue" in chosen else [],
                "dropped": dropped,
                "uncertain": uncertain,
                "by_kit": bool(by_kit),
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
