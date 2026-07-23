from contextlib import asynccontextmanager

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from httpx import AsyncClient, AsyncBaseTransport, Limits
import httpx

FURSEE_BASE = "http://localhost:58898"

router = APIRouter(prefix="/fursee")

_client: AsyncClient | None = None


def set_client(client: AsyncClient):
    global _client
    _client = client


@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
async def proxy(request: Request, path: str):
    client = _client
    if client is None:
        return StreamingResponse(
            content='{"error": "proxy not ready"}',
            status_code=503,
            media_type="application/json",
        )

    qs = request.url.query
    url = f"{FURSEE_BASE}/{path}" + (f"?{qs}" if qs else "")

    body = await request.body()

    headers = {
        k: v
        for k, v in request.headers.items()
        if k.lower() not in ("host", "content-length", "connection", "upgrade")
    }

    try:
        response = await client.request(
            method=request.method,
            url=url,
            headers=headers,
            content=body,
        )
    except httpx.ConnectError:
        return StreamingResponse(
            content='{"error": "upstream unavailable"}',
            status_code=502,
            media_type="application/json",
        )

    resp_headers = dict(response.headers)
    resp_headers.pop("transfer-encoding", None)

    return StreamingResponse(
        content=response.aiter_bytes(),
        status_code=response.status_code,
        headers=resp_headers,
        media_type=response.headers.get("content-type"),
    )


@router.websocket("/api/ws/{task_id}")
async def proxy_ws(websocket: WebSocket, task_id: str):
    await websocket.accept()

    try:
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "GET",
                f"{FURSEE_BASE}/api/ws/{task_id}",
                headers={"Upgrade": "websocket", "Connection": "upgrade"},
            ) as response:
                pass
    except Exception:
        await websocket.send_json({"event": "error", "message": "upstream unavailable"})
        await websocket.close()
        return

    import asyncio
    import json

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
