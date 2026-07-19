"""FastAPI application — main assembly point."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from starlette.middleware.sessions import SessionMiddleware

from app.config import CORS_ORIGINS, PROJECT_ROOT, PANEL_PASSWORD, SESSION_SECRET
from app.database import engine, Base
from app.dependencies import verify_panel_auth
from app.routers import tracking, stats


@asynccontextmanager
async def lifespan(application: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield
    engine.dispose()


app = FastAPI(
    title="Ant Cave Analytics",
    version="1.0.0",
    description="Simple website visitor tracking and analytics API.",
    lifespan=lifespan,
)

app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET, max_age=86400)

origins = [o.strip() for o in CORS_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tracking.router)
app.include_router(stats.router)


class LoginRequest(BaseModel):
    password: str


@app.post("/api/login", include_in_schema=False)
def login(request: Request, body: LoginRequest):
    if not PANEL_PASSWORD:
        request.session["panel_authenticated"] = True
        return {"status": "ok"}
    if body.password == PANEL_PASSWORD:
        request.session["panel_authenticated"] = True
        return {"status": "ok"}
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid password")


@app.post("/api/logout", include_in_schema=False)
def logout(request: Request):
    request.session.pop("panel_authenticated", None)
    return {"status": "ok"}


@app.get("/api/auth/check", include_in_schema=False)
def auth_check(request: Request):
    if not PANEL_PASSWORD:
        return {"authenticated": True}
    if request.session.get("panel_authenticated") is True:
        return {"authenticated": True}
    return JSONResponse({"authenticated": False}, status_code=status.HTTP_401_UNAUTHORIZED)


@app.get("/dashboard", include_in_schema=False)
def get_dashboard(_auth=Depends(verify_panel_auth)):
    path = PROJECT_ROOT / "static" / "dashboard.html"
    if path.exists():
        return FileResponse(str(path), media_type="text/html")
    return {"error": "Dashboard page not found"}


@app.get("/tracker.js", include_in_schema=False)
def get_tracker_js():
    path = PROJECT_ROOT / "static" / "tracker.js"
    if path.exists():
        return FileResponse(
            str(path),
            media_type="application/javascript",
            headers={"Cache-Control": "public, max-age=3600"},
        )
    return {"error": "Tracker script not found"}
