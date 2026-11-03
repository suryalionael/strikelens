"""StrikeLens API entry point."""

from fastapi import FastAPI

app = FastAPI(title="StrikeLens API", version="0.0.1")


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness check."""
    return {"status": "ok"}
