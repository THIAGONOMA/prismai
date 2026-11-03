from __future__ import annotations

import contextvars
from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from prismai.auth.jwt import decode_access_token

_bearer = HTTPBearer(auto_error=False)

current_org_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("current_org_id", default=None)
current_user_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("current_user_id", default=None)


@dataclass(frozen=True)
class Identity:
    org_id: str
    sub: str


async def get_identity(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> Identity:
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")
    try:
        payload = decode_access_token(credentials.credentials)
    except Exception as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token") from exc

    org_id = payload.get("org_id")
    sub = payload.get("sub")
    if not org_id or not sub:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Malformed token")

    current_org_id.set(org_id)
    current_user_id.set(sub)
    return Identity(org_id=org_id, sub=sub)


async def get_optional_identity(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> Identity | None:
    """Same as get_identity but returns None instead of 401 when no token is present."""
    if credentials is None:
        return None
    try:
        payload = decode_access_token(credentials.credentials)
    except Exception:
        return None

    org_id = payload.get("org_id")
    sub = payload.get("sub")
    if not org_id or not sub:
        return None

    current_org_id.set(org_id)
    current_user_id.set(sub)
    return Identity(org_id=org_id, sub=sub)
