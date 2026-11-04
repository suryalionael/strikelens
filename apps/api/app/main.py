"""StrikeLens API entry point."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import sessionmaker

from app.db import Base, cors_origins, database_url, make_engine
from app.models import tables  # noqa: F401  (registers the tables on Base)
from app.routes import fighters, fights, stats, tags


def create_app(db_url: str | None = None) -> FastAPI:
    """Build the app. Tests pass a temporary database URL."""
    engine = make_engine(db_url or database_url())

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        Base.metadata.create_all(engine)
        yield
        engine.dispose()

    app = FastAPI(title="StrikeLens API", version="0.0.1", lifespan=lifespan)
    app.state.sessionmaker = sessionmaker(engine, expire_on_commit=False)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins(),
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(fighters.router)
    app.include_router(fights.router)
    app.include_router(tags.router)
    app.include_router(stats.router)

    @app.get("/health")
    def health() -> dict[str, str]:
        """Liveness check."""
        return {"status": "ok"}

    return app


app = create_app()
