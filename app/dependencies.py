"""FastAPI dependencies for route handlers."""

from fastapi import HTTPException, Request, status

from app.config import PANEL_PASSWORD


def verify_panel_auth(request: Request):
    """Verify the panel session. Skips check if no password is configured."""
    if not PANEL_PASSWORD:
        return True
    if request.session.get("panel_authenticated") is True:
        return True
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")


def serve_dashboard(request: Request):
    """Serve dashboard HTML; let frontend handle auth check if password is set."""
    if not PANEL_PASSWORD:
        return True
    if request.session.get("panel_authenticated") is True:
        return True
    return False


def get_client_ip(request: Request) -> str:
    """Extract the real client IP from the request.

    Checks X-Forwarded-For first (for reverse proxies),
    then falls back to request.client.host.
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        ip = forwarded.split(",")[0].strip()
        if ip:
            return ip
    if request.client:
        return request.client.host
    return "unknown"
