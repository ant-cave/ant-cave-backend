import asyncio
import json

from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect, status
from fastapi.responses import StreamingResponse
from httpx import AsyncClient
import httpx

FURSEE_BASE = "http://localhost:58898"

router = APIRouter(prefix="/fursee")

_client: AsyncClient | None = None


def set_client(client: AsyncClient):
    global _client
    _client = client


def _get_user_sub(request: Request) -> str | None:
    return request.session.get("user_sub")


def _require_user(request: Request):
    sub = _get_user_sub(request)
    if not sub:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return sub


def _prefix_user(path: str, sub: str, method: str, body: bytes | None) -> tuple[str, bytes | None]:
    if method == "POST" and path.endswith("/pipeline/auto") and body:
        try:
            data = json.loads(body)
            existing = data.get("existing_run_id", "")
            if existing:
                data["existing_run_id"] = f"{sub}_{existing}"
            return path, json.dumps(data).encode()
        except json.JSONDecodeError:
            pass
    return path, body


def _filter_json_by_user(data: dict, sub: str) -> dict:
    key = None
    if "runs" in data:
        key = "runs"
        items = data["runs"]
    elif "tasks" in data:
        key = "tasks"
        items = data["tasks"]
    else:
        return data

    filtered = [item for item in items if str(item.get("run_id", item.get("task_id", ""))).startswith(f"{sub}_")]
    data[key] = filtered
    if "count" in data:
        data["count"] = len(filtered)
    return data


@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
async def proxy(request: Request, path: str):
    client = _client
    if client is None:
        return StreamingResponse(content='{"error": "proxy not ready"}', status_code=503, media_type="application/json")

    sub = _get_user_sub(request)

    need_auth = path.startswith("api/")
    if need_auth and not sub:
        return StreamingResponse(content='{"error": "Not authenticated"}', status_code=401, media_type="application/json")

    qs = request.url.query
    body = await request.body()

    target_path, body = _prefix_user(path, sub, request.method, body) if sub else (path, body)

    if sub and "auto_uploads" in target_path:
        target_path = target_path.replace("auto_uploads", f"auto_uploads_{sub}")

    url = f"{FURSEE_BASE}/{target_path}" + (f"?{qs}" if qs else "")

    headers = {
        k: v
        for k, v in request.headers.items()
        if k.lower() not in ("host", "content-length", "connection", "upgrade")
    }
    if sub:
        headers["X-User-Sub"] = sub

    try:
        response = await client.request(
            method=request.method,
            url=url,
            headers=headers,
            content=body,
        )
    except httpx.ConnectError:
        return StreamingResponse(content='{"error": "upstream unavailable"}', status_code=502, media_type="application/json")

    content_type = response.headers.get("content-type", "")
    if sub and "application/json" in content_type:
        try:
            raw = await response.aread()
            data = json.loads(raw)
            data = _filter_json_by_user(data, sub)
            return StreamingResponse(
                content=json.dumps(data),
                status_code=response.status_code,
                headers={k: v for k, v in response.headers.items() if k.lower() not in ("transfer-encoding", "content-length")},
                media_type="application/json",
            )
        except (json.JSONDecodeError, Exception):
            pass

    resp_headers = dict(response.headers)
    resp_headers.pop("transfer-encoding", None)

    return StreamingResponse(
        content=response.aiter_bytes(),
        status_code=response.status_code,
        headers=resp_headers,
        media_type=content_type,
    )


@router.websocket("/api/ws/{task_id}")
async def proxy_ws(websocket: WebSocket, task_id: str):
    await websocket.accept()

    try:
        from websockets.asyncio.client import connect as ws_connect
    except ImportError:
        try:
            from websockets.client import connect as ws_connect
        except ImportError:
            await websocket.send_json({"event": "error", "message": "websockets library not installed"})
            await websocket.close()
            return

    upstream_uri = f"ws://localhost:58898/api/ws/{task_id}"

    try:
        async with ws_connect(upstream_uri) as upstream:
            async def forward_upstream_to_client():
                async for msg in upstream:
                    if isinstance(msg, str):
                        await websocket.send_text(msg)
                    else:
                        await websocket.send_bytes(msg)

            async def forward_client_to_upstream():
                while True:
                    try:
                        msg = await websocket.receive_text()
                        await upstream.send(msg)
                    except WebSocketDisconnect:
                        break

            await asyncio.gather(
                forward_upstream_to_client(),
                forward_client_to_upstream(),
            )
    except Exception as e:
        try:
            await websocket.send_json({"event": "error", "message": str(e)})
        except Exception:
            pass
        finally:
            try:
                await websocket.close()
            except Exception:
                pass
