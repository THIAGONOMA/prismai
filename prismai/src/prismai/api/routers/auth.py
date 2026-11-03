from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from prismai.auth.jwt import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/v1/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    org_name: str
    username: str
    password: str


class TokenRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


_orgs: dict[str, dict] = {}
_users: dict[str, dict] = {}


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(body: RegisterRequest):
    if body.username in _users:
        raise HTTPException(409, "Username already taken")

    import uuid

    org_id = str(uuid.uuid4())
    _orgs[org_id] = {"id": org_id, "name": body.org_name}
    _users[body.username] = {
        "username": body.username,
        "hashed_password": hash_password(body.password),
        "org_id": org_id,
    }
    token = create_access_token(org_id=org_id, sub=body.username)
    return TokenResponse(access_token=token)


@router.post("/token", response_model=TokenResponse)
async def login(body: TokenRequest):
    user = _users.get(body.username)
    if not user or not verify_password(body.password, user["hashed_password"]):
        raise HTTPException(401, "Invalid credentials")
    token = create_access_token(org_id=user["org_id"], sub=body.username)
    return TokenResponse(access_token=token)


def reset_auth_store() -> None:
    _orgs.clear()
    _users.clear()
