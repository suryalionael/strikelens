# cv/configs/

TOML configs for pipeline runs, read with Python's standard `tomllib`, so no extra
dependency is needed. Configs are small text files and are safe to commit. They
hold settings only, never paths to footage.

- `ingest.toml`: frame rate, JPEG quality, and cut detection for `strikelens-cv ingest`.
- `track.toml`: YOLO weights file, confidence, the red and blue matching, and the referee filter's skin ranges for `strikelens-cv track`.
- `segments.toml`: when a run of short shots is suggested as a replay (`strikelens-cv suggest`, also run by ingest).
- `pose.toml`: pose backend, model file, box margin, and lowest pose confidence for `strikelens-cv pose`.
- `rounds.toml`: where to look for the broadcast scoreboard and how its time on screen becomes rounds (`strikelens-cv rounds`, also run by ingest).
- `windows.toml`: training window length, samples, missing data, negatives, and the validation split for `strikelens-cv windows`.
- `infer.toml`: the model, how often to score, and the peak threshold and gap for `strikelens-cv suggest-strikes`.
