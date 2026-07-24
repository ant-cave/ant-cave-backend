import secrets
import hashlib
import base64
import json
import httpx

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import RedirectResponse, JSONResponse
from pydantic import BaseModel

from app.config import OAUTH_CLIENT_ID, OAUTH_CLIENT_SECRET, OAUTH_REDIRECT_URI
from app.database import SessionLocal
from app.models import User

AUTH_BASE = "https://account-api.qzhua.net"
TOKEN_URL = f"{AUTH_BASE}/oauth2/token"
USERINFO_URL = f"{AUTH_BASE}/oauth2/userinfo"
AUTHORIZE_URL = f"{AUTH_BASE}/oauth2/authorize"

router = APIRouter(prefix="/api/auth", tags=["auth"])


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    id_token: str | None = None
    scope: str
    token_type: str
    expires_in: int


class UserInfo(BaseModel):
    sub: str
    username: str | None = None
    email: str | None = None
    picture: str | None = None


class CodeExchangeRequest(BaseModel):
    code: str
    code_verifier: str


def _base64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _sha256(s: str) -> str:
    return _base64url(hashlib.sha256(s.encode()).digest())


def _random_string(length: int = 64) -> str:
    return secrets.token_urlsafe(length)[:length]


@router.get("/login")
async def login(request: Request, redirect: str = ""):
    if request.session.get("user_sub"):
        return {"authenticated": True, "user": _get_user_from_session(request)}

    code_verifier = _random_string(64)
    code_challenge = _sha256(code_verifier)
    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)

    if redirect:
        request.session["oauth_redirect"] = redirect

    params = {
        "response_type": "code",
        "client_id": OAUTH_CLIENT_ID,
        "redirect_uri": OAUTH_REDIRECT_URI,
        "scope": "openid profile",
        "state": state,
        "nonce": nonce,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    qs = "&".join(f"{k}={_urlencode(v)}" for k, v in params.items())
    return {"authorize_url": f"{AUTHORIZE_URL}?{qs}", "code_verifier": code_verifier, "state": state}


@router.post("/token")
async def exchange_token(body: CodeExchangeRequest, request: Request):
    print(f"[EXCHANGE] code={body.code[:20]}..., code_verifier={body.code_verifier[:20]}...")
    print(f"[EXCHANGE] TOKEN_URL={TOKEN_URL}, CLIENT_ID={OAUTH_CLIENT_ID}, REDIRECT_URI={OAUTH_REDIRECT_URI}")
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "client_id": OAUTH_CLIENT_ID,
                "client_secret": OAUTH_CLIENT_SECRET,
                "code": body.code,
                "redirect_uri": OAUTH_REDIRECT_URI,
                "code_verifier": body.code_verifier,
            },
        )
        print(f"[EXCHANGE] token response status={token_resp.status_code}, body={token_resp.text}")
        if token_resp.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Token exchange failed: {token_resp.status_code} {token_resp.text}",
            )

        token_data = token_resp.json()
        access_token = token_data["access_token"]
        id_token = token_data.get("id_token", "")
        print(f"[EXCHANGE] got access_token={access_token[:20]}..., id_token={'yes' if id_token else 'no'}")

        userinfo = {}
        if id_token:
            payload = id_token.split(".")[1]
            pad = 4 - len(payload) % 4
            if pad != 4:
                payload += "=" * pad
            try:
                userinfo = json.loads(base64.urlsafe_b64decode(payload))
                print(f"[EXCHANGE] parsed id_token: sub={userinfo.get('sub')}, username={userinfo.get('username')}")
            except Exception as e:
                print(f"[EXCHANGE] failed to parse id_token: {e}")

        if not userinfo.get("sub"):
            userinfo_resp = await client.get(
                USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
                follow_redirects=True,
            )
            print(f"[EXCHANGE] userinfo response status={userinfo_resp.status_code}, body={userinfo_resp.text[:300]}")
            if userinfo_resp.status_code != 200:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Failed to get user info")
            userinfo = userinfo_resp.json()

    sub = userinfo["sub"]
    print(f"[EXCHANGE] user sub={sub}")
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.sub == sub).first()
        print(f"[EXCHANGE] existing user={user}")
        if not user:
            user = User(
                sub=sub,
                username=userinfo.get("username", ""),
                email=userinfo.get("email", ""),
                picture=userinfo.get("picture", ""),
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            print(f"[EXCHANGE] created new user id={user.id}")
        else:
            user.username = userinfo.get("username", user.username)
            user.email = userinfo.get("email", user.email)
            user.picture = userinfo.get("picture", user.picture)
            db.commit()
            print(f"[EXCHANGE] updated existing user id={user.id}")
    finally:
        db.close()

    request.session["user_sub"] = user.sub
    request.session["user_username"] = user.username
    request.session["user_picture"] = user.picture
    print(f"[EXCHANGE] session set, redirecting")

    redirect_to = request.session.pop("oauth_redirect", "/fursee/auto")
    return {"status": "ok", "redirect": redirect_to}


@router.get("/me")
async def me(request: Request):
    sub = request.session.get("user_sub")
    if not sub:
        return JSONResponse({"authenticated": False}, status_code=status.HTTP_401_UNAUTHORIZED)

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.sub == sub).first()
        if not user:
            return JSONResponse({"authenticated": False}, status_code=status.HTTP_401_UNAUTHORIZED)
        return {
            "authenticated": True,
            "sub": user.sub,
            "username": user.username,
            "email": user.email,
            "picture": user.picture,
        }
    finally:
        db.close()


@router.post("/logout")
async def logout(request: Request):
    request.session.pop("user_sub", None)
    request.session.pop("user_username", None)
    request.session.pop("user_picture", None)
    return {"status": "ok"}


def _get_user_from_session(request: Request) -> dict | None:
    sub = request.session.get("user_sub")
    if not sub:
        return None
    return {
        "sub": sub,
        "username": request.session.get("user_username", ""),
        "picture": request.session.get("user_picture", ""),
    }


def _urlencode(s: str) -> str:
    import urllib.parse
    return urllib.parse.quote(s, safe="")
