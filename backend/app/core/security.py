"""Password hashing, JWT and secret encryption."""
from __future__ import annotations

import base64
import hashlib
import hmac
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt
from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings
from app.core.exceptions import Unauthorized

# ---------- passwords ----------

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


# ---------- JWT ----------

def create_token(subject: int | str, token_type: str, extra: dict[str, Any] | None = None,
                 expires_minutes: int | None = None) -> str:
    if expires_minutes is None:
        expires_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES if token_type == "admin" else settings.USER_TOKEN_EXPIRE_MINUTES
    now = datetime.now(timezone.utc)
    payload = {"sub": str(subject), "typ": token_type, "iat": now, "exp": now + timedelta(minutes=expires_minutes)}
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except jwt.ExpiredSignatureError as e:
        raise Unauthorized("登录已过期，请重新登录") from e
    except jwt.PyJWTError as e:
        raise Unauthorized("无效的身份凭证") from e


# ---------- symmetric encryption for API keys ----------

def _fernet() -> Fernet:
    key = settings.ENCRYPTION_KEY
    if not key:
        digest = hashlib.sha256(("enc:" + settings.SECRET_KEY).encode()).digest()
        key = base64.urlsafe_b64encode(digest).decode()
    return Fernet(key.encode())


def encrypt_secret(plain: str) -> str:
    return _fernet().encrypt(plain.encode("utf-8")).decode()


def decrypt_secret(cipher: str) -> str:
    try:
        return _fernet().decrypt(cipher.encode()).decode("utf-8")
    except InvalidToken as e:
        raise RuntimeError("无法解密 API Key，请检查 ENCRYPTION_KEY/SECRET_KEY 是否变更") from e


def mask_secret(plain: str) -> str:
    if not plain:
        return ""
    if len(plain) <= 8:
        return "****"
    return f"{plain[:3]}****{plain[-4:]}"


# ---------- signed URLs for private files ----------

def sign_file_url(file_id: int, ttl_seconds: int = 3600) -> tuple[int, str]:
    exp = int(time.time()) + ttl_seconds
    sig = hmac.new(settings.SECRET_KEY.encode(), f"file:{file_id}:{exp}".encode(), hashlib.sha256).hexdigest()[:32]
    return exp, sig


def verify_file_sig(file_id: int, exp: int, sig: str) -> bool:
    if exp < time.time():
        return False
    expected = hmac.new(settings.SECRET_KEY.encode(), f"file:{file_id}:{exp}".encode(), hashlib.sha256).hexdigest()[:32]
    return hmac.compare_digest(expected, sig)
