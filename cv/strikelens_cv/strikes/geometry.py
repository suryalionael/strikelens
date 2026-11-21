"""Strikes from pose geometry: rules over both fighters' keypoints, no training.

Ported from mma-vision by Binyam Abraha (https://github.com/BinyamAbraha/mma-vision,
AGPL-3.0, reuse agreed with the author): `tracks.py` (keypoint cleanup) and
`strikes.py` (the detector). Changes in the port, see ADR 0011:

- Plain Python, no numpy, so the rules are unit-tested in CI.
- Times are in milliseconds and speeds in torso-heights per second, so the
  thresholds work at any frame rate (mma-vision counted frames at about 30 fps;
  StrikeLens extracts 10 fps by default).
- MediaPipe's 33 landmarks instead of COCO-17 (the 17 used are in both).
- Every candidate keeps its verdict, including the kick foot-lift check, so a
  missed strike can be traced to the gate that dropped it.

A strike is a speed peak of a wrist or ankle moving toward the opponent. Impact is
the closest approach to the opponent after the peak. It is kept only if the limb
is extended and has travelled, the peak has neighbouring frames (not a keypoint
jump), and the limb is not cooling down. It landed if the tip reaches the target
(head, body, legs) or the opponent's head snaps; a body or leg kick also needs
the opponent's hips to move. Blocked strikes are not told apart: they read as
landed or missed, and the analyst corrects them.
"""

import math
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from statistics import median
from typing import Any, Literal, TypedDict

Point = tuple[float, float]
Corner = Literal["red", "blue"]
Kind = Literal["punch", "kick"]

# MediaPipe Pose 33 indices of the joints the rules use (the COCO-17 subset).
JOINTS: dict[str, int] = {
    "nose": 0,
    "l_eye": 2,
    "r_eye": 5,
    "l_ear": 7,
    "r_ear": 8,
    "l_shoulder": 11,
    "r_shoulder": 12,
    "l_elbow": 13,
    "r_elbow": 14,
    "l_wrist": 15,
    "r_wrist": 16,
    "l_hip": 23,
    "r_hip": 24,
    "l_knee": 25,
    "r_knee": 26,
    "l_ankle": 27,
    "r_ankle": 28,
}
FACE = ("nose", "l_eye", "r_eye", "l_ear", "r_ear")
# Striking tip -> (anchor joint, kind). Elbows and knees are not detected yet.
LIMBS: dict[str, tuple[str, Kind]] = {
    "l_wrist": ("l_shoulder", "punch"),
    "r_wrist": ("r_shoulder", "punch"),
    "l_ankle": ("l_hip", "kick"),
    "r_ankle": ("r_hip", "kick"),
}
# (child, parent, longest possible length in torso-heights). Parents first, so a
# stolen elbow also drops the wrist on it. A 2D projection can only shorten a limb.
LIMB_LIMITS = (
    ("l_elbow", "l_shoulder", 0.85),
    ("r_elbow", "r_shoulder", 0.85),
    ("l_knee", "l_hip", 1.0),
    ("r_knee", "r_hip", 1.0),
    ("l_wrist", "l_elbow", 0.85),
    ("r_wrist", "r_elbow", 0.85),
    ("l_ankle", "l_knee", 1.0),
    ("r_ankle", "r_knee", 1.0),
)


@dataclass(frozen=True)
class GeometryConfig:
    """Thresholds from mma-vision's config.yaml, converted from frames at 30 fps."""

    min_visibility: float = 0.3
    scale_window_ms: int = 1500
    gap_ms: int = 200
    max_step_ms: int = 250
    smooth_alpha_30fps: float = 0.65
    max_limb_len: float = 1.0
    punch_speed: float = 4.8
    kick_speed: float = 6.0
    clinch_range: float = 0.9
    clinch_speed_mult: float = 1.25
    max_react_speed: float = 15.0
    min_kick_lift: float = 0.3
    kick_lift_ms: int = 300
    toward_cos: float = 0.3
    min_ext_punch: float = 0.5
    min_ext_kick: float = 0.6
    min_punch_travel: float = 0.35
    min_kick_travel: float = 0.5
    min_reach: float = 0.3
    impact_ms_punch: int = 200
    impact_ms_kick: int = 400
    lookback_ms: int = 300
    land_dist: float = 0.35
    land_dist_kick_tight: float = 0.12
    head_react_speed: float = 0.9
    body_react_speed: float = 1.5
    react_ms: int = 200
    react_baseline_ms: int = 300
    cut_guard_ms: int = 300
    cooldown_ms_punch: int = 300
    cooldown_ms_kick: int = 500
    min_gap_ms: int = 150
    combo_ms: int = 500
    combo_relax: float = 0.6
    max_miss_dist_punch: float = 0.9
    max_miss_dist_kick: float = 1.4
    miss_speed_mult: float = 1.3
    support_ms: int = 100
    support_frac: float = 0.2
    min_support: int = 1

    def __post_init__(self) -> None:
        for name, value in asdict(self).items():
            if value < 0:
                raise ValueError(f"{name} must be at least 0")
        if not 0 < self.smooth_alpha_30fps <= 1:
            raise ValueError("smooth_alpha_30fps must be above 0 and at most 1")
        if not -1 <= self.toward_cos <= 1:
            raise ValueError("toward_cos must be between -1 and 1")
        if not 0 < self.combo_relax <= 1:
            raise ValueError("combo_relax must be above 0 and at most 1")


class Candidate(TypedDict):
    time_ms: int
    peak_ms: int
    fighter: Corner
    limb: str
    kind: Kind
    weapon: str
    target: str
    landed: bool
    confidence: float
    speed: float
    toward: float
    extension: float
    travel: float | None
    reach: float | None
    land_dist: float
    head_react: float
    body_react: float
    range: float | None
    support: int
    in_combo: bool
    in_clinch: bool
    rejected_by: str


# Small vector helpers. None stands for an unknown point or value.


def _sub(a: Point, b: Point) -> Point:
    return (a[0] - b[0], a[1] - b[1])


def _norm(v: Point) -> float:
    return math.hypot(v[0], v[1])


def _dist(a: Point | None, b: Point | None) -> float | None:
    return None if a is None or b is None else _norm(_sub(a, b))


def _mean(points: Sequence[Point | None]) -> Point | None:
    known = [p for p in points if p is not None]
    if not known:
        return None
    return (sum(p[0] for p in known) / len(known), sum(p[1] for p in known) / len(known))


def _seg_dist(p: Point, a: Point | None, b: Point | None) -> float | None:
    """Distance from p to the segment a-b."""
    if a is None or b is None:
        return None
    ab = _sub(b, a)
    length2 = ab[0] ** 2 + ab[1] ** 2
    t = (
        0.0
        if length2 < 1e-9
        else max(0.0, min(1.0, ((p[0] - a[0]) * ab[0] + (p[1] - a[1]) * ab[1]) / length2))
    )
    return _norm(_sub(p, (a[0] + t * ab[0], a[1] + t * ab[1])))


@dataclass
class Series:
    """One fighter's cleaned keypoints on the shared time grid."""

    times: list[int]
    joints: dict[str, list[Point | None]]
    scale: list[float]

    def pt(self, name: str) -> list[Point | None]:
        return self.joints[name]

    def mid(self, a: str, b: str) -> list[Point | None]:
        return [_mean([p, q]) for p, q in zip(self.joints[a], self.joints[b], strict=True)]

    def head(self) -> list[Point | None]:
        return [_mean([self.joints[f][i] for f in FACE]) for i in range(len(self.times))]

    def hip_center(self) -> list[Point | None]:
        return self.mid("l_hip", "r_hip")

    def torso_center(self) -> list[Point | None]:
        sh, hp = self.mid("l_shoulder", "r_shoulder"), self.hip_center()
        return [_mean([a, b]) for a, b in zip(sh, hp, strict=True)]


def build_series(
    times: Sequence[int],
    frames: Mapping[int, Mapping[str, Any]],
    cuts: Sequence[bool],
    config: GeometryConfig,
) -> Series:
    """Clean one fighter's keypoints: drop unsure and impossible joints, fill short
    gaps, smooth (reset at camera cuts), and measure torso height for the scale.

    `frames` maps a time to a keypoint frame ({"keypoints": 33 x [x, y, z, v] or None,
    "box": [x1, y1, x2, y2] or None}); `cuts[i]` is True where a new shot starts."""
    n = len(times)
    joints: dict[str, list[Point | None]] = {name: [None] * n for name in JOINTS}
    boxes: list[Sequence[float] | None] = [None] * n
    for i, t in enumerate(times):
        frame = frames.get(t)
        if not frame:
            continue
        boxes[i] = frame.get("box")
        kps = frame.get("keypoints")
        if kps is None:
            continue
        for name, idx in JOINTS.items():
            x, y, _z, vis = kps[idx]
            if vis >= config.min_visibility:
                joints[name][i] = (float(x), float(y))

    scale = _torso_scale(times, joints, boxes, config.scale_window_ms)
    for child, parent, limit in LIMB_LIMITS:
        c, p = joints[child], joints[parent]
        for i in range(n):
            d = _dist(c[i], p[i])
            if d is not None and d / scale[i] > limit * config.max_limb_len:
                c[i] = None
    for name in JOINTS:
        joints[name] = _fill_gaps(times, joints[name], config.gap_ms)
        joints[name] = _smooth(times, joints[name], cuts, config.smooth_alpha_30fps)
    return Series(list(times), joints, scale)


def _torso_scale(
    times: Sequence[int],
    joints: Mapping[str, list[Point | None]],
    boxes: Sequence[Sequence[float] | None],
    window_ms: int,
) -> list[float]:
    """Rolling median of torso height (shoulder-mid to hip-mid) in pixels, filled
    from the nearest known value. Falls back to 0.35 of the box height, then 100."""
    n = len(times)
    torso: list[float | None] = []
    for i in range(n):
        sh = _mean([joints["l_shoulder"][i], joints["r_shoulder"][i]])
        hp = _mean([joints["l_hip"][i], joints["r_hip"][i]])
        torso.append(_dist(sh, hp))
    if all(v is None for v in torso):
        heights = [b[3] - b[1] for b in boxes if b is not None]
        fallback = 0.35 * median(heights) if heights else 100.0
        return [max(fallback, 1e-3)] * n
    half = window_ms / 2
    rolled: list[float | None] = []
    lo = hi = 0
    for i in range(n):
        while times[lo] < times[i] - half:
            lo += 1
        while hi < n and times[hi] <= times[i] + half:
            hi += 1
        known = [v for v in torso[lo:hi] if v is not None]
        rolled.append(median(known) if len(known) >= 3 else None)
    # Fill from the nearest known value on either side.
    filled: list[float] = []
    last: float | None = None
    for v in rolled:
        last = v if v is not None else last
        filled.append(last if last is not None else -1.0)
    nxt: float | None = None
    for i in range(n - 1, -1, -1):
        if rolled[i] is not None:
            nxt = rolled[i]
        if filled[i] < 0:
            filled[i] = nxt if nxt is not None else median([v for v in torso if v is not None])
    return [max(v, 1e-3) for v in filled]


def _fill_gaps(times: Sequence[int], pts: list[Point | None], gap_ms: int) -> list[Point | None]:
    """Linear interpolation across a run of unknowns no longer than `gap_ms`."""
    out = list(pts)
    i = 0
    while i < len(out):
        if out[i] is not None:
            i += 1
            continue
        j = i
        while j < len(out) and out[j] is None:
            j += 1
        a, b = out[i - 1] if i > 0 else None, out[j] if j < len(out) else None
        if (
            a is not None
            and b is not None
            and times[j] - times[i - 1] <= gap_ms + (times[j] - times[j - 1])
        ):
            t0, t1 = times[i - 1], times[j]
            for k in range(i, j):
                f = (times[k] - t0) / (t1 - t0)
                out[k] = (a[0] + f * (b[0] - a[0]), a[1] + f * (b[1] - a[1]))
        i = j
    return out


def _smooth(
    times: Sequence[int], pts: list[Point | None], cuts: Sequence[bool], alpha_30fps: float
) -> list[Point | None]:
    """Exponential smoothing with the weight of `alpha_30fps` per 1/30 s, so it is the
    same at any frame rate. Restarts at a cut, so a cut is not smeared into a swing."""
    if alpha_30fps >= 1:
        return list(pts)
    out: list[Point | None] = list(pts)
    prev: Point | None = None
    for i, p in enumerate(pts):
        if p is None or (i > 0 and cuts[i]):
            prev = p
            continue
        if prev is not None and i > 0:
            steps = max(1.0, (times[i] - times[i - 1]) / (1000 / 30))
            a = 1 - (1 - alpha_30fps) ** steps
            p = (a * p[0] + (1 - a) * prev[0], a * p[1] + (1 - a) * prev[1])
            out[i] = p
        prev = p
    return out


def _velocity(
    times: Sequence[int], pts: Sequence[Point | None], scale: Sequence[float], max_step_ms: int
) -> list[Point | None]:
    """Velocity in torso-heights per second, from each sample and the one before."""
    out: list[Point | None] = [None]
    for i in range(1, len(pts)):
        a, b, dt = pts[i - 1], pts[i], times[i] - times[i - 1]
        if a is None or b is None or dt <= 0 or dt > max_step_ms:
            out.append(None)
        else:
            k = 1000 / dt / scale[i]
            out.append(((b[0] - a[0]) * k, (b[1] - a[1]) * k))
    return out


def _speeds(vel: Sequence[Point | None], cap: float | None = None) -> list[float | None]:
    out: list[float | None] = []
    for v in vel:
        s = None if v is None else _norm(v)
        out.append(None if s is None or (cap is not None and s > cap) else s)
    return out


def _window(times: Sequence[int], start_ms: float, end_ms: float) -> range:
    """Indices with start_ms <= time <= end_ms (times are sorted)."""
    lo = next((i for i, t in enumerate(times) if t >= start_ms), len(times))
    hi = lo
    while hi < len(times) and times[hi] <= end_ms:
        hi += 1
    return range(lo, hi)


def _peaks(
    times: Sequence[int], speed: Sequence[float | None], mask: Sequence[bool], cooldown_ms: int
) -> list[int]:
    """Local speed maxima where `mask` holds, at least `cooldown_ms` apart (the faster wins)."""

    def s(i: int) -> float:
        v = speed[i]
        return -math.inf if v is None else v

    cand = [
        i for i in range(1, len(speed) - 1) if mask[i] and s(i) >= s(i - 1) and s(i) >= s(i + 1)
    ]
    picked: list[int] = []
    for i in sorted(cand, key=lambda i: -s(i)):
        if all(abs(times[i] - times[j]) >= cooldown_ms for j in picked):
            picked.append(i)
    return sorted(picked)


def _target_dists(tip: Point, opp: Series, i: int, kind: Kind) -> dict[str, float]:
    """Distance (torso-heights) from the tip to each target region of the opponent."""
    scale = opp.scale[i]
    out: dict[str, float] = {}
    head = _mean([opp.joints[f][i] for f in FACE])
    d = _dist(tip, head)
    if d is not None:
        out["head"] = max(0.0, d / scale - 0.18)
    sh = _mean([opp.joints["l_shoulder"][i], opp.joints["r_shoulder"][i]])
    hp = _mean([opp.joints["l_hip"][i], opp.joints["r_hip"][i]])
    d = _seg_dist(tip, sh, hp)
    if d is not None:
        out["body"] = max(0.0, d / scale - 0.25)
    if kind == "kick":
        legs = [
            _seg_dist(tip, opp.joints[f"{s}_{a}"][i], opp.joints[f"{s}_{b}"][i])
            for s in ("l", "r")
            for a, b in (("hip", "knee"), ("knee", "ankle"))
        ]
        known = [x for x in legs if x is not None]
        if known:
            out["legs"] = max(0.0, min(known) / scale - 0.12)
    return out


def _zone(tip: Point, opp: Series, i: int, kind: Kind) -> str:
    """head, body, or legs by the tip's height against the opponent's shoulders and hips."""
    scale = opp.scale[i]
    sh = _mean([opp.joints["l_shoulder"][i], opp.joints["r_shoulder"][i]])
    hp = _mean([opp.joints["l_hip"][i], opp.joints["r_hip"][i]])
    if sh is None or hp is None:
        return "body"
    if tip[1] < sh[1] + 0.12 * scale:  # at or above the shoulder line; image y grows down
        return "head"
    if kind == "kick" and tip[1] > hp[1] + 0.15 * scale:
        return "legs"
    return "body"


def _reaction(
    times: Sequence[int], speed: Sequence[float | None], imp: int, config: GeometryConfig
) -> float:
    """Peak speed just after impact, above the median just before it."""
    t = times[imp]
    before = [speed[k] for k in _window(times, t - config.react_baseline_ms, t - 1)]
    base_known = [v for v in before if v is not None]
    base = median(base_known) if base_known else 0.0
    after = [speed[k] for k in _window(times, t, t + config.react_ms)]
    known = [v for v in after if v is not None]
    return max(known) - base if known else 0.0


def weapon_for(kind: Kind, limb: str, me: Series, opp_center: Point | None, i: int) -> str:
    """A first guess at the weapon: a kick, or a jab from the lead hand and a cross
    from the rear hand. The lead hand's shoulder is the one nearer the opponent.
    Hooks, uppercuts, teeps, knees, and elbows are left for the analyst."""
    if kind == "kick":
        return "kick"
    side = limb[0]
    other = "r" if side == "l" else "l"
    d_mine = _dist(me.joints[f"{side}_shoulder"][i], opp_center)
    d_other = _dist(me.joints[f"{other}_shoulder"][i], opp_center)
    if d_mine is None or d_other is None:
        return "jab"
    return "jab" if d_mine <= d_other else "cross"


def detect(
    series: Mapping[Corner, Series], cuts: Sequence[bool], config: GeometryConfig
) -> list[Candidate]:
    """Every strike candidate with its verdict, in time order. Accepted strikes have
    `rejected_by == ""`."""
    times = series["red"].times
    cut_times = [times[i] for i, c in enumerate(cuts) if c]
    raw: list[dict[str, Any]] = []
    rejected: list[Candidate] = []
    for me_name, opp_name in (("red", "blue"), ("blue", "red")):
        me, opp = series[me_name], series[opp_name]  # type: ignore[index]
        opp_center = opp.torso_center()
        hips_me, hips_opp = me.hip_center(), opp.hip_center()
        opp_head_speed = _speeds(
            _velocity(times, opp.head(), opp.scale, config.max_step_ms), config.max_react_speed
        )
        opp_body_speed = _speeds(
            _velocity(times, hips_opp, opp.scale, config.max_step_ms), config.max_react_speed
        )
        for limb, (anchor, kind) in LIMBS.items():
            pos, anc = me.pt(limb), me.pt(anchor)
            vel = _velocity(times, pos, me.scale, config.max_step_ms)
            speed = _speeds(vel)
            toward: list[float | None] = []
            for i, v in enumerate(vel):
                to_opp = (
                    None if pos[i] is None or opp_center[i] is None else _sub(opp_center[i], pos[i])
                )  # type: ignore[arg-type]
                if v is None or to_opp is None or _norm(v) < 1e-9 or _norm(to_opp) < 1e-9:
                    toward.append(None)
                else:
                    toward.append(
                        (v[0] * to_opp[0] + v[1] * to_opp[1]) / (_norm(v) * _norm(to_opp))
                    )
            threshold = config.punch_speed if kind == "punch" else config.kick_speed
            mask = [
                s is not None and c is not None and s > threshold and c > config.toward_cos
                for s, c in zip(speed, toward, strict=True)
            ]
            cooldown = config.cooldown_ms_punch if kind == "punch" else config.cooldown_ms_kick
            for p in _peaks(times, speed, mask, cooldown):
                t = times[p]
                peak_speed = speed[p] or 0.0
                near = [
                    speed[k]
                    for k in _window(times, t - config.support_ms, t + config.support_ms)
                    if k != p
                ]
                support = sum(
                    1 for v in near if v is not None and v > config.support_frac * peak_speed
                )
                window_ms = config.impact_ms_punch if kind == "punch" else config.impact_ms_kick
                win = [
                    k
                    for k in _window(times, t, t + window_ms)
                    if pos[k] is not None and opp_center[k] is not None
                ]
                if not win:
                    continue
                imp = min(win, key=lambda k: _dist(pos[k], opp_center[k]) or math.inf)
                tip = pos[imp]
                ext = _dist(tip, anc[imp])
                if tip is None or ext is None:
                    continue
                scale = me.scale[imp]
                prior = [
                    pos[k]
                    for k in _window(times, t - config.lookback_ms, t - 1)
                    if pos[k] is not None
                ]
                travel = max((_norm(_sub(q, tip)) for q in prior), default=None)  # type: ignore[arg-type]
                reach = None
                if anc[imp] is not None and opp_center[imp] is not None:
                    d = _sub(opp_center[imp], anc[imp])  # type: ignore[arg-type]
                    if _norm(d) > 1e-6:
                        off = _sub(tip, anc[imp])  # type: ignore[arg-type]
                        reach = (off[0] * d[0] + off[1] * d[1]) / _norm(d) / scale
                dists = _target_dists(tip, opp, imp, kind)
                if not dists:
                    continue
                target = _zone(tip, opp, imp, kind)
                if dists.get("head", math.inf) < config.land_dist:
                    target = "head"  # a glove on the head is a head shot, however low the head is
                if target not in dists:
                    target = min(dists, key=lambda k: dists[k])
                hip_gap = _dist(hips_me[imp], hips_opp[imp])
                rng = None if hip_gap is None else hip_gap / ((me.scale[imp] + opp.scale[imp]) / 2)
                candidate = {
                    "time_ms": times[imp],
                    "peak_ms": t,
                    "fighter": me_name,
                    "limb": limb,
                    "kind": kind,
                    "weapon": weapon_for(kind, limb, me, opp_center[imp], imp),
                    "target": target,
                    "landed": False,
                    "confidence": 0.0,
                    "speed": round(peak_speed, 3),
                    "toward": round(toward[p] or 0.0, 3),
                    "extension": round(ext / scale, 3),
                    "travel": None if travel is None else round(travel / scale, 3),
                    "reach": None if reach is None else round(reach, 3),
                    "land_dist": round(dists[target], 3),
                    "head_react": round(_reaction(times, opp_head_speed, imp, config), 3),
                    "body_react": round(_reaction(times, opp_body_speed, imp, config), 3),
                    "range": None if rng is None else round(rng, 3),
                    "support": support,
                    "in_combo": False,
                    "in_clinch": False,
                    "rejected_by": "",
                }
                if kind == "kick":
                    # Walking moves an ankle toward the opponent too; a kick lifts the
                    # foot well above the standing ankle. Image y grows downward.
                    other = me.pt("r_ankle" if limb == "l_ankle" else "l_ankle")
                    lifts = [
                        (other[k][1] - pos[k][1]) / me.scale[k]  # type: ignore[index]
                        for k in _window(times, t, t + config.kick_lift_ms)
                        if other[k] is not None and pos[k] is not None
                    ]
                    if not lifts or max(lifts) < config.min_kick_lift:
                        rejected.append({**candidate, "rejected_by": "no_foot_lift"})  # type: ignore[typeddict-item]
                        continue
                near_cut = any(abs(c - times[imp]) <= config.cut_guard_ms for c in cut_times)
                candidate["near_cut"] = near_cut
                raw.append(candidate)
    return sorted(_gate(raw, config) + rejected, key=lambda c: (c["time_ms"], c["fighter"]))


def _gate(raw: list[dict[str, Any]], config: GeometryConfig) -> list[Candidate]:
    """Second pass, in time order per fighter: apply the gates. Inside a combination
    the extension, reach, and travel gates are relaxed (fighters do not fully retract
    between punches)."""
    out: list[Candidate] = []
    last_strike: dict[str, int] = {}
    last_limb: dict[tuple[str, str], int] = {}
    for c in sorted(raw, key=lambda d: (d["time_ms"], -d["speed"])):
        near_cut = c.pop("near_cut")
        kind, me, limb, t = c["kind"], c["fighter"], c["limb"], c["time_ms"]
        in_combo = me in last_strike and 0 < t - last_strike[me] <= config.combo_ms
        relax = config.combo_relax if in_combo else 1.0
        in_clinch = c["range"] is not None and c["range"] < config.clinch_range
        threshold = config.punch_speed if kind == "punch" else config.kick_speed
        if in_clinch:
            threshold *= config.clinch_speed_mult
        c["in_combo"], c["in_clinch"] = in_combo, in_clinch
        cooldown = config.cooldown_ms_punch if kind == "punch" else config.cooldown_ms_kick
        min_ext = config.min_ext_punch if kind == "punch" else config.min_ext_kick
        min_travel = config.min_punch_travel if kind == "punch" else config.min_kick_travel
        reason = ""
        if near_cut:
            reason = "camera_cut"
        elif c["support"] < config.min_support:
            reason = "keypoint_jump"
        elif me in last_strike and 0 <= t - last_strike[me] < config.min_gap_ms:
            reason = "too_soon"
        elif (me, limb) in last_limb and 0 <= t - last_limb[(me, limb)] < cooldown:
            reason = "same_limb_too_soon"
        elif c["speed"] < threshold:
            reason = "slow_in_clinch" if in_clinch else "slow"
        elif c["reach"] is not None and c["reach"] < config.min_reach * relax:
            reason = "no_reach"
        elif c["extension"] < min_ext * relax:
            reason = "not_extended"
        elif c["travel"] is not None and c["travel"] < min_travel * relax:
            reason = "no_travel"
        if not reason:
            dist, head, speed = c["land_dist"], c["head_react"], c["speed"]
            if kind == "kick" and c["target"] in ("body", "legs"):
                # 2D cannot tell a foot short in depth from one that lands, but a
                # landed kick moves the opponent: very close, or close and a shove.
                shoved = c["body_react"] > config.body_react_speed
                landed = dist < config.land_dist_kick_tight or (
                    dist < 1.5 * config.land_dist and shoved
                )
            else:
                snapped = head > config.head_react_speed
                landed = dist < config.land_dist or (dist < 1.5 * config.land_dist and snapped)
            max_miss = config.max_miss_dist_punch if kind == "punch" else config.max_miss_dist_kick
            if not landed and dist > max_miss:
                reason = "miss_too_far"
            elif not landed and speed < threshold * config.miss_speed_mult:
                reason = "miss_too_slow"
            else:
                c["landed"] = landed
                c["confidence"] = round(
                    max(
                        0.0,
                        min(
                            1.0,
                            0.5 * max(0.0, min(1.0, 1 - dist / (2 * config.land_dist)))
                            + 0.3 * max(0.0, min(1.0, head / (2 * config.head_react_speed)))
                            + 0.2 * max(0.0, min(1.0, (speed - threshold) / threshold)),
                        ),
                    ),
                    3,
                )
                last_strike[me] = t
                last_limb[(me, limb)] = t
        c["rejected_by"] = reason
        out.append(c)  # type: ignore[arg-type]
    return out
