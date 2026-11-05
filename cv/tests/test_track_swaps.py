from strikelens_cv.track import count_swaps, iou
from strikelens_cv.track.assign import Box, TrackFrame

LEFT: Box = [0, 0, 100, 300]
RIGHT: Box = [300, 0, 400, 300]


def frame(index: int, red: Box | None, blue: Box | None) -> TrackFrame:
    return {"index": index, "timestamp_ms": index * 100, "red": red, "blue": blue}


def test_iou() -> None:
    assert iou(LEFT, LEFT) == 1
    assert iou(LEFT, RIGHT) == 0
    assert iou([0, 0, 10, 10], [5, 0, 15, 10]) == 50 / 150
    assert iou(None, LEFT) == 0


def test_no_swaps() -> None:
    truth = [frame(i, LEFT, RIGHT) for i in range(5)]
    assert count_swaps(truth, truth) == {"swaps": 0, "swapped_frames": 0, "compared_frames": 5}


def test_one_run_is_one_swap() -> None:
    truth = [frame(i, LEFT, RIGHT) for i in range(6)]
    auto = [frame(i, RIGHT, LEFT) if 2 <= i <= 4 else frame(i, LEFT, RIGHT) for i in range(6)]
    assert count_swaps(auto, truth) == {"swaps": 1, "swapped_frames": 3, "compared_frames": 6}


def test_two_separate_runs() -> None:
    truth = [frame(i, LEFT, RIGHT) for i in range(6)]
    auto = [frame(i, RIGHT, LEFT) if i in (1, 4) else frame(i, LEFT, RIGHT) for i in range(6)]
    assert count_swaps(auto, truth)["swaps"] == 2


def test_one_box_on_the_wrong_corner_counts() -> None:
    truth = [frame(0, LEFT, RIGHT)]
    assert count_swaps([frame(0, None, LEFT)], truth)["swaps"] == 1


def test_missing_boxes_are_not_swaps_and_empty_truth_is_skipped() -> None:
    truth = [frame(0, LEFT, RIGHT), frame(1, None, None)]
    auto = [frame(0, None, None), frame(1, RIGHT, LEFT)]
    assert count_swaps(auto, truth) == {"swaps": 0, "swapped_frames": 0, "compared_frames": 1}
