# cv/configs/

TOML configs for pipeline runs, read with Python's standard `tomllib`, so no extra
dependency is needed. Configs are small text files and are safe to commit. They
hold settings only, never paths to footage.

- `ingest.toml`: frame rate, JPEG quality, and cut detection for `strikelens-cv ingest`.
- `segments.toml`: when a run of short shots is suggested as a replay (`strikelens-cv suggest`, also run by ingest).
