from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class AdminLoginIn(BaseModel):
    username: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=1, max_length=128)


class WechatLoginIn(BaseModel):
    code: str = Field(..., min_length=1, max_length=256)
    nickname: str | None = Field(None, max_length=64)
    avatar_url: str | None = Field(None, max_length=512)
    # Only honoured when WECHAT_DEV_LOGIN=true and no AppID is configured (stable identity in dev tools).
    dev_openid: str | None = Field(None, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")


class AdminOut(ORMModel):
    id: int
    username: str
    display_name: str | None
    role: str
    is_active: bool
    last_login_at: datetime | None
    created_at: datetime


class UserOut(ORMModel):
    id: int
    nickname: str | None
    avatar_url: str | None
    status: str
    created_at: datetime
    last_login_at: datetime | None


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    principal_type: str
    profile: dict
