"""FastAPI dependencies for route handlers."""

from fastapi import Request


def get_client_ip(request: Request) -> str:
    """Extract the real client IP from the request.

    Checks X-Forwarded-For first (for reverse proxies),
    then falls back to request.client.host.
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # Take the first IP in the chain
        ip = forwarded.split(",")[0].strip()
        if ip:
            return ip
    # Fallback to direct client address
    if request.client:
        return request.client.host
    return "unknown"
