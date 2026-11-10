"""Authentication dependencies and role checks. All authorization happens server side."""
from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import Forbidden, Unauthorized
from app.core.security import decode_token
from app.models import AdminUser, User

bearer = HTTPBearer(auto_error=False)

ROLE_LEVEL = {"viewer": 1, "admin": 2, "super_admin": 3}


@dataclass
class Principal:
    kind: str  # "admin" | "user"
    admin: AdminUser | None = None
    user: User | None = None

    @property
    def is_admin(self) -> bool:
        return self.kind == "admin"

    @property
    def id(self) -> int:
        return self.admin.id if self.admin else self.user.id  # type: ignore[union-attr]


def _load_principal(creds: HTTPAuthorizationCredentials | None, db: Session) -> Principal:
    if creds is None or creds.scheme.lower() != "bearer":
        raise Unauthorized()
    payload = decode_token(creds.credentials)
    typ, sub = payload.get("typ"), payload.get("sub")
    if not sub or typ not in ("admin", "user"):
        raise Unauthorized("无效的身份凭证")
    if typ == "admin":
        admin = db.get(AdminUser, int(sub))
        if not admin or admin.deleted_at is not None or not admin.is_active:
            raise Unauthorized("管理员账号不可用")
        return Principal(kind="admin", admin=admin)
    user = db.get(User, int(sub))
    if not user or user.deleted_at is not None:
        raise Unauthorized("用户不存在")
    if user.status != "active":
        raise Forbidden("账号已被禁用")
    return Principal(kind="user", user=user)


def get_principal(request: Request, creds: HTTPAuthorizationCredentials | None = Depends(bearer),
                  db: Session = Depends(get_db)) -> Principal:
    p = _load_principal(creds, db)
    request.state.principal = p
    return p


def get_current_admin(p: Principal = Depends(get_principal)) -> AdminUser:
    if not p.is_admin:
        raise Forbidden("需要管理员权限")
    return p.admin  # type: ignore[return-value]


def get_current_user(p: Principal = Depends(get_principal)) -> User:
    if p.is_admin:
        raise Forbidden("该接口仅限小程序用户访问")
    return p.user  # type: ignore[return-value]


def require_role(min_role: str):
    """Dependency factory: admin must have at least `min_role`."""
    need = ROLE_LEVEL[min_role]

    def _dep(admin: AdminUser = Depends(get_current_admin)) -> AdminUser:
        if ROLE_LEVEL.get(admin.role, 0) < need:
            raise Forbidden(f"需要 {min_role} 及以上角色")
        return admin

    return _dep


# Convenience aliases
AdminReader = Depends(require_role("viewer"))
AdminWriter = Depends(require_role("admin"))
SuperAdmin = Depends(require_role("super_admin"))
