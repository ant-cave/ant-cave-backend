"""FastAPI application — main assembly point."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.config import CORS_ORIGINS, PROJECT_ROOT
from app.database import engine, Base
from app.routers import tracking, stats


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Create tables on startup and dispose pool on shutdown."""
    Base.metadata.create_all(bind=engine)
    yield
    engine.dispose()


# ── App ───────────────────────────────────────────────────

app = FastAPI(
    title="Ant Cave Analytics",
    version="1.0.0",
    description="Simple website visitor tracking and analytics API.",
    lifespan=lifespan,
)

# CORS
origins = [o.strip() for o in CORS_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(tracking.router)
app.include_router(stats.router)


# ── Static file routes ────────────────────────────────────


@app.get("/dashboard", include_in_schema=False)
def get_dashboard():
    """Serve the analytics dashboard HTML."""
    path = PROJECT_ROOT / "static" / "dashboard.html"
    if path.exists():
        return FileResponse(str(path), media_type="text/html")
    return {"error": "Dashboard page not found"}


@app.get("/tracker.js", include_in_schema=False)
def get_tracker_js():
    """Serve the tracking JavaScript snippet."""
    path = PROJECT_ROOT / "static" / "tracker.js"
    if path.exists():
        return FileResponse(
            str(path),
            media_type="application/javascript",
            headers={"Cache-Control": "public, max-age=3600"},
        )
    return {"error": "Tracker script not found"}
