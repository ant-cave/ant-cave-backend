import asyncio
import json
import time

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
        print(f"[代理] 错误：代理未就绪，请求路径={path}")
        return StreamingResponse(content='{"error": "proxy not ready"}', status_code=503, media_type="application/json")

    sub = _get_user_sub(request)

    need_auth = path.startswith("api/")
    if need_auth and not sub:
        print(f"[代理] 未认证请求被拒绝，路径={path}，方法={request.method}")
        return StreamingResponse(content='{"error": "Not authenticated"}', status_code=401, media_type="application/json")

    qs = request.url.query
    body = await request.body()
    body_size = len(body)

    target_path, body = _prefix_user(path, sub, request.method, body) if sub else (path, body)

    url = f"{FURSEE_BASE}/{target_path}" + (f"?{qs}" if qs else "")

    is_upload = "upload" in target_path.lower()
    is_pipeline = "pipeline" in target_path.lower()
    start_time = time.time()
    print(f"[代理] 收到请求：方法={request.method} 路径=/{target_path} 用户={sub or '匿名'} 大小={body_size}字节" +
          (f"（文件上传）" if is_upload else f"（流水线任务）" if is_pipeline else ""))

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
        elapsed = time.time() - start_time
        print(f"[代理] 上游响应：路径=/{target_path} 状态={response.status_code} 耗时={elapsed:.2f}s")
    except httpx.ConnectError:
        elapsed = time.time() - start_time
        print(f"[代理] 连接上游失败：路径=/{target_path} 耗时={elapsed:.2f}s")
        return StreamingResponse(content='{"error": "upstream unavailable"}', status_code=502, media_type="application/json")
    except httpx.ReadError as e:
        elapsed = time.time() - start_time
        print(f"[代理] 读取上游响应失败：路径=/{target_path} 错误={e} 耗时={elapsed:.2f}s")
        return StreamingResponse(content='{"error": "upstream read error"}', status_code=502, media_type="application/json")
    except httpx.TimeoutException:
        elapsed = time.time() - start_time
        print(f"[代理] 上游超时：路径=/{target_path} 耗时={elapsed:.2f}s")
        return StreamingResponse(content='{"error": "upstream timeout"}', status_code=504, media_type="application/json")

    content_type = response.headers.get("content-type", "")
    print(f"[代理] 响应 content-type={content_type}，用户={sub or '匿名'}，状态={response.status_code}")
    if sub and "application/json" in content_type:
        try:
            raw = await response.aread()
            print(f"[代理] JSON响应体前200字符: {raw[:200]}")
            data = json.loads(raw)
            return StreamingResponse(
                content=json.dumps(data),
                status_code=response.status_code,
                headers={k: v for k, v in response.headers.items() if k.lower() not in ("transfer-encoding", "content-length")},
                media_type="application/json",
            )
        except (json.JSONDecodeError, Exception) as e:
            print(f"[代理] JSON解析失败: {e}，前200字符: {raw[:200] if raw else '空'}")

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
    print(f"[WebSocket代理] 客户端连接，任务 id={task_id}")

    try:
        from websockets.asyncio.client import connect as ws_connect
    except ImportError:
        try:
            from websockets.client import connect as ws_connect
        except ImportError:
            print(f"[WebSocket代理] 错误：websockets 库未安装")
            await websocket.send_json({"event": "error", "message": "websockets library not installed"})
            await websocket.close()
            return

    upstream_uri = f"ws://localhost:58898/api/ws/{task_id}"
    print(f"[WebSocket代理] 正在连接上游 {upstream_uri}")

    try:
        async with ws_connect(upstream_uri) as upstream:
            print(f"[WebSocket代理] 上游连接成功，任务 id={task_id}")
            async def forward_upstream_to_client():
                msg_count = 0
                async for msg in upstream:
                    msg_count += 1
                    if isinstance(msg, str):
                        data_preview = msg[:100] if len(msg) > 100 else msg
                        print(f"[WebSocket代理] 上游→客户端 第{msg_count}条: {data_preview}")
                        await websocket.send_text(msg)
                    else:
                        print(f"[WebSocket代理] 上游→客户端 第{msg_count}条: 二进制数据 {len(msg)}字节")
                        await websocket.send_bytes(msg)

            async def forward_client_to_upstream():
                while True:
                    try:
                        msg = await websocket.receive_text()
                        print(f"[WebSocket代理] 客户端→上游: {msg[:100] if len(msg) > 100 else msg}")
                        await upstream.send(msg)
                    except WebSocketDisconnect:
                        print(f"[WebSocket代理] 客户端断开，任务 id={task_id}")
                        break

            await asyncio.gather(
                forward_upstream_to_client(),
                forward_client_to_upstream(),
            )
    except Exception as e:
        print(f"[WebSocket代理] 异常：任务 id={task_id}，错误={e}")
        try:
            await websocket.send_json({"event": "error", "message": str(e)})
        except Exception:
            pass
        finally:
            try:
                await websocket.close()
            except Exception:
                pass
