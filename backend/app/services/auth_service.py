from __future__ import annotations

import logging

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import utcnow
from app.core.exceptions import BadRequest, Forbidden, Unauthorized, UpstreamError
from app.core.security import create_token, verify_password
from app.models import AdminUser, User
from app.schemas.auth import AdminOut, UserOut

logger = logging.getLogger(__name__)


def admin_login(db: Session, username: str, password: str) -> dict:
    admin = db.scalars(select(AdminUser).where(AdminUser.username == username, AdminUser.deleted_at.is_(None))).first()
    if admin is None or not verify_password(password, admin.password_hash):
        raise Unauthorized("用户名或密码错误")
    if not admin.is_active:
        raise Forbidden("账号已停用")
    admin.last_login_at = utcnow()
    db.commit()
    token = create_token(admin.id, "admin", {"role": admin.role})
    return {"access_token": token, "token_type": "bearer", "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "principal_type": "admin", "profile": AdminOut.model_validate(admin).model_dump(mode="json")}


def code_to_session(code: str, dev_openid: str | None = None) -> dict:
    """Exchange wx.login code for openid via WeChat jscode2session."""
    if not settings.WECHAT_APPID or not settings.WECHAT_SECRET:
        if settings.WECHAT_DEV_LOGIN:
            # Development only: fake openid (stable when the client sends a persisted dev_openid)
            return {"openid": f"dev_{(dev_openid or code)[:40]}"}
        raise BadRequest("服务端未配置 WECHAT_APPID / WECHAT_SECRET")
    try:
        resp = httpx.get("https://api.weixin.qq.com/sns/jscode2session", timeout=10, params={
            "appid": settings.WECHAT_APPID, "secret": settings.WECHAT_SECRET, "js_code": code,
            "grant_type": "authorization_code"})
        data = resp.json()
    except Exception as e:
        raise UpstreamError("微信登录服务不可用") from e
    if data.get("errcode"):
        logger.warning("jscode2session errcode=%s", data.get("errcode"))
        raise Unauthorized(f"微信登录失败({data.get('errcode')})")
    return data


def wechat_login(db: Session, code: str, nickname: str | None, avatar_url: str | None,
                 dev_openid: str | None = None) -> dict:
    info = code_to_session(code, dev_openid)
    openid = info["openid"]
    user = db.scalars(select(User).where(User.openid == openid)).first()
    if user is None:
        user = User(openid=openid, unionid=info.get("unionid"), nickname=nickname or "微信用户",
                    avatar_url=avatar_url, status="active")
        db.add(user)
    else:
        if user.deleted_at is not None:
            raise Forbidden("账号已注销")
        if user.status != "active":
            raise Forbidden("账号已被禁用")
        if nickname:
            user.nickname = nickname
        if avatar_url:
            user.avatar_url = avatar_url
    user.last_login_at = utcnow()
    db.commit()
    token = create_token(user.id, "user")
    return {"access_token": token, "token_type": "bearer", "expires_in": settings.USER_TOKEN_EXPIRE_MINUTES * 60,
            "principal_type": "user", "profile": UserOut.model_validate(user).model_dump(mode="json")}
