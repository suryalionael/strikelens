"""overlay stage: boxes, skeletons, and a strike timeline drawn onto the fight.

For the Gate 2 demo video, and (with --ids) for writing track corrections. Reads
the output of ingest, track, and pose, plus fight.json (rounds) and tags.json
(confirmed tags), all under data/processed/<fight>/. Writes:

- overlay.mp4 / overlay-round-<N>.mp4           red and blue boxes, skeletons,
                                                and the strike timeline
- overlay-ids.mp4 / overlay-ids-round-<N>.mp4   every person with shot and track ID

core.py decides what to draw and is pure. render.py draws it with OpenCV and
encodes it with FFmpeg.
"""

from strikelens_cv.overlay.config import (
    DEFAULT_OVERLAY_CONFIG,
    OverlayConfig,
    load_overlay_config,
)
from strikelens_cv.overlay.core import (
    SKELETON,
    confirmed_tags,
    corner_owners,
    corner_shapes,
    frames_to_render,
    id_shapes,
    output_name,
    render_span,
    skeleton_shapes,
    timeline_shapes,
)
from strikelens_cv.overlay.render import OverlayResult, encoder_command, overlay

__all__ = [
    "DEFAULT_OVERLAY_CONFIG",
    "SKELETON",
    "OverlayConfig",
    "OverlayResult",
    "confirmed_tags",
    "corner_owners",
    "corner_shapes",
    "encoder_command",
    "frames_to_render",
    "id_shapes",
    "load_overlay_config",
    "output_name",
    "overlay",
    "render_span",
    "skeleton_shapes",
    "timeline_shapes",
]
