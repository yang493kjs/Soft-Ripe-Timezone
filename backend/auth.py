# -*- coding: utf-8 -*-
"""认证、会话管理、速率限制 与 Pydantic 模型"""
import hashlib
import secrets
import time as _time_module
import threading
from typing import Optional

from fastapi import HTTPException, Header
from pydantic import BaseModel

from settings import (
    SESSION_TOKENS, TOKEN_EXPIRY, RATE_LIMIT_BUCKETS, _RATE_LIMIT_LOCK,
    SESSION_TOKENS as _S, TOKEN_EXPIRY as _E, RATE_LIMIT_BUCKETS as _R, _RATE_LIMIT_LOCK as _L
)

# ==================== Session Token ====================

def _create_session_token(username: str) -> str:
    token = secrets.token_hex(32)
    SESSION_TOKENS[token] = {
        "username": username,
        "user_id": username,
        "expires_at": _time_module.time() + TOKEN_EXPIRY
    }
    now = _time_module.time()
    for t in list(SESSION_TOKENS.keys()):
        if SESSION_TOKENS[t]["expires_at"] < now:
            del SESSION_TOKENS[t]
    return token


def _verify_session_token(token: str) -> dict | None:
    session = SESSION_TOKENS.get(token)
    if not session:
        return None
    if session["expires_at"] < _time_module.time():
        del SESSION_TOKENS[token]
        return None
    session["expires_at"] = _time_module.time() + TOKEN_EXPIRY
    return {"username": session["username"], "user_id": session["user_id"]}


# ==================== Rate Limiting ====================

def _check_rate_limit(user_id: str, max_per_minute: int = 8) -> bool:
    with _RATE_LIMIT_LOCK:
        now = _time_module.time()
        window = now - 60
        if user_id not in RATE_LIMIT_BUCKETS:
            RATE_LIMIT_BUCKETS[user_id] = []
        RATE_LIMIT_BUCKETS[user_id] = [t for t in RATE_LIMIT_BUCKETS[user_id] if t > window]
        if len(RATE_LIMIT_BUCKETS[user_id]) >= max_per_minute:
            return False
        RATE_LIMIT_BUCKETS[user_id].append(now)
        for uid in list(RATE_LIMIT_BUCKETS.keys()):
            if not RATE_LIMIT_BUCKETS.get(uid) or (RATE_LIMIT_BUCKETS[uid] and RATE_LIMIT_BUCKETS[uid][-1] < now - 300):
                del RATE_LIMIT_BUCKETS[uid]
        return True


# ==================== Auth Dependency ====================

async def require_auth(authorization: str | None = Header(None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="请先登录")
    token = authorization[7:]
    user = _verify_session_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")
    return user


# ==================== Password Hashing ====================

def _hash_password(password: str, salt: str = None) -> tuple:
    if salt is None:
        salt = secrets.token_hex(16)
    h = hashlib.sha256((password + salt).encode('utf-8')).hexdigest()
    return h, salt


# ==================== Pydantic Models ====================

class UserProfile(BaseModel):
    username: str
    created_at: str
    last_active: str


class UserRequest(BaseModel):
    username: str
    password: Optional[str] = None


class ChatRequest(BaseModel):
    user_id: str = "default_user"
    persona_id: str = "sunny"
    message: str
    user_is_typing: bool = False
    image_base64: Optional[str] = None
    image_mime_type: str = "image/png"


class ConfigRequest(BaseModel):
    api_key: str
    base_url: str = ""
    model: str = ""


class FrontendError(BaseModel):
    source: str = "frontend"
    message: str
    stack: Optional[str] = None
    url: Optional[str] = None
    user_id: str = "default_user"
    persona_id: str = "sunny"
