"""Split a track where ByteTrack passed its ID from one person to another (#64).

When two people overlap, ByteTrack can carry one ID from a fighter to the
referee, or from red to blue. Red and blue are assigned per track, so a mixed
track puts a corner's box on the wrong person for part of a shot. A track is cut
where its chest changes sharply between the samples before and after (the kit
colour or the dark share), or where its box jumps sideways. Each piece then goes
through assignment on its own.

Pure Python on plain detection lists, so it is tested in CI.
"""

from collections import defaultdict
from collections.abc import Sequence
from itertools import pairwise
from statistics import median

from strikelens_cv.track.assign import Detection
from strikelens_cv.track.config import TrackConfig


def _kit_gap(d: Detection) -> float:
    return (d.get("torso_red") or 0.0) - (d.get("torso_blue") or 0.0)


def _centre(d: Detection) -> float:
    return (d["box"][0] + d["box"][2]) / 2


def _width(d: Detection) -> float:
    return max(1.0, d["box"][2] - d["box"][0])


def cut_points(track: Sequence[Detection], config: TrackConfig) -> list[int]:
    """Where to cut one track's detections (in frame order): each index starts a piece.

    Compares the median of the `split_window` samples before and after each point.
    Cuts are at least a window apart, so one change is not cut twice.
    """
    k = config.split_window
    gaps = [_kit_gap(d) for d in track]
    darks = [d.get("torso_dark") or 0.0 for d in track]
    cuts: list[int] = []
    for i in range(k, len(track) - k + 1):
        if cuts and i - cuts[-1] < k:
            continue
        before, after = slice(i - k, i), slice(i, i + k)
        kit_jump = abs(median(gaps[before]) - median(gaps[after]))
        dark_jump = abs(median(darks[before]) - median(darks[after]))
        move = abs(_centre(track[i]) - _centre(track[i - 1])) / _width(track[i - 1])
        if move > config.split_move:
            cuts.append(i)
        elif kit_jump > config.split_kit_jump:
            cuts.append(_first_like_after(gaps, i, k))
        elif dark_jump > config.split_dark_jump:
            cuts.append(_first_like_after(darks, i, k))
    return cuts


def _first_like_after(values: Sequence[float], i: int, k: int) -> int:
    """The median after `i` flips once most of the next `k` samples are the new
    person, so the change can be up to k / 2 samples later. Cut at the first sample
    that is closer to the new person than to the old one."""
    before, after = median(values[i - k : i]), median(values[i : i + k])
    for j in range(i, min(i + k, len(values))):
        if abs(values[j] - after) < abs(values[j] - before):
            return j
    return i


def split_switches(detections: Sequence[Detection], config: TrackConfig) -> list[Detection]:
    """The detections with each mixed track cut into pieces.

    The first piece keeps its track ID, so corrections to tracks that never switch
    still apply. Later pieces get new IDs above the highest one in their shot.
    Every detection keeps ByteTrack's own ID as `bytetrack_id`.
    """
    tracks: dict[tuple[int, int], list[Detection]] = defaultdict(list)
    for d in detections:
        tracks[(d["shot"], d["track_id"])].append(d)
    next_id: dict[int, int] = defaultdict(int)
    for shot, track_id in tracks:
        next_id[shot] = max(next_id[shot], track_id)

    out: list[Detection] = []
    for (shot, track_id), items in sorted(tracks.items()):
        items = sorted(items, key=lambda d: d["frame"])
        bounds = [0, *cut_points(items, config), len(items)]
        for piece, (start, end) in enumerate(pairwise(bounds)):
            new_id = track_id
            if piece > 0:
                next_id[shot] += 1
                new_id = next_id[shot]
            for d in items[start:end]:
                copy: Detection = {**d, "track_id": new_id}
                copy["bytetrack_id"] = d.get("bytetrack_id", track_id)
                out.append(copy)
    return sorted(out, key=lambda d: (d["frame"], d["track_id"]))


def is_split(detections: Sequence[Detection]) -> bool:
    """Whether these detections went through `split_switches` already."""
    return all("bytetrack_id" in d for d in detections)
