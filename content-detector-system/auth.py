"""
JWT-based authentication.
Endpoints: POST /auth/register, POST /auth/login, GET /auth/me
Roles: admin, analyst (default)
"""

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from database import create_user, get_user

logger = logging.getLogger("auth")

_SECRET = os.environ.get("JWT_SECRET", "change-me-in-production")
_ALGORITHM = "HS256"
_TOKEN_EXPIRE_MINUTES = int(os.environ.get("JWT_EXPIRE_MINUTES", "60"))

_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
_oauth2 = OAuth2PasswordBearer(tokenUrl="/auth/login")

router = APIRouter(prefix="/auth", tags=["auth"])


# ---- models ----

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = _TOKEN_EXPIRE_MINUTES * 60


class UserOut(BaseModel):
    username: str
    role: str
    created_at: str


class RegisterRequest(BaseModel):
    username: str
    password: str
    role: str = "analyst"


# ---- helpers ----

def _hash_password(plain: str) -> str:
    return _pwd_ctx.hash(plain)


def _verify_password(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


def _create_token(username: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=_TOKEN_EXPIRE_MINUTES)
    return jwt.encode(
        {"sub": username, "role": role, "exp": expire},
        _SECRET, algorithm=_ALGORITHM,
    )


async def get_current_user(token: str = Depends(_oauth2)) -> dict:
    try:
        payload = jwt.decode(token, _SECRET, algorithms=[_ALGORITHM])
        username: str = payload.get("sub", "")
        role: str = payload.get("role", "analyst")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid token")
        return {"username": username, "role": role}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def require_role(*roles: str):
    """Dependency factory: raises 403 if user's role is not in allowed roles."""
    async def _check(user: dict = Depends(get_current_user)) -> dict:
        if user["role"] not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return _check


# ---- endpoints ----

@router.post("/register", response_model=UserOut, status_code=201)
async def register(req: RegisterRequest):
    if await get_user(req.username):
        raise HTTPException(status_code=409, detail="Username already exists")
    if req.role not in ("admin", "analyst"):
        raise HTTPException(status_code=400, detail="Role must be 'admin' or 'analyst'")
    hashed = _hash_password(req.password)
    await create_user(req.username, hashed, req.role)
    logger.info("New user registered: %s (role=%s)", req.username, req.role)
    user = await get_user(req.username)
    return UserOut(username=user["username"], role=user["role"], created_at=user["created_at"])


@router.post("/login", response_model=TokenResponse)
async def login(form: OAuth2PasswordRequestForm = Depends()):
    user = await get_user(form.username)
    if not user or not _verify_password(form.password, user["hashed_pw"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = _create_token(user["username"], user["role"])
    logger.info("User logged in: %s", user["username"])
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserOut)
async def me(current_user: dict = Depends(get_current_user)):
    user = await get_user(current_user["username"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserOut(username=user["username"], role=user["role"], created_at=user["created_at"])
