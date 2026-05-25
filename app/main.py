"""
MLB Database & API — FastAPI application entry point.

Run with:
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.games import router as games_router
from app.api.players import router as players_router
from app.api.stats import router as stats_router
from app.api.teams import router as teams_router
from app.database import async_engine

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle management."""
    yield
    # Dispose of the connection pool on shutdown
    await async_engine.dispose()


app = FastAPI(
    title="MLB Stats API",
    description=(
        "Personal MLB statistics API with at-bat-level data and custom split queries. "
        "Supports batting, pitching, and stolen-base stats with extensive filters."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# Allow the UI to call the API from any origin (personal use)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(players_router, prefix="/api/v1")
app.include_router(teams_router, prefix="/api/v1")
app.include_router(games_router, prefix="/api/v1")
app.include_router(stats_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    """Basic health check."""
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
async def root():
    """Serve the explorer UI."""
    return FileResponse(STATIC_DIR / "index.html")


# Mount static files last so API routes take priority
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
