"""ingest stage: extract frames with FFmpeg and find camera cuts with PySceneDetect.

Output for one fight, under data/processed/<fight>/:

- frames/000000.jpg ...  frame N is at N * 1000 / fps ms from the start of the file
- frames.json            every frame with its file name and timestamp_ms
- cuts.json              shots between camera cuts, as start_ms and end_ms
- segment-suggestions.json  likely replays from the cut list (see strikelens_cv.segments)
- ingest.json            the settings used, for reproducibility

Timestamps count from the start of the video file, the same clock the tagger uses.
"""

from strikelens_cv.ingest.config import IngestConfig, load_config
from strikelens_cv.ingest.run import IngestResult, ingest

__all__ = ["IngestConfig", "IngestResult", "ingest", "load_config"]
