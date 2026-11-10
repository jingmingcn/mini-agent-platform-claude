from datetime import date, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import BadRequest, Conflict, NotFound
from app.core.permissions import get_current_user, require_role
from app.core.response import ok
from app.core.security import hash_password
from app.models import AdminUser, Conversation, UsageStatistic, User
from app.schemas.auth import AdminOut, UserOut
from app.services.audit_service import audit

router = APIRouter(tags=["用户"])


class UserStatusIn(BaseModel):
    status: Literal["active", "disabled"]


class AdminCreateIn(BaseModel):
    username: str = Field(..., min_length=3, max_length=64, pattern=r"^[A-Za-z0-9_.-]+$")
    password: str = Field(..., min_length=8, max_length=128)
    display_name: str | None = Field(None, max_length=64)
    role: Literal["super_admin", "admin", "viewer"] = "admin"


class AdminUpdateIn(BaseModel):
    password: str | None = Field(None, min_length=8, max_length=128)
    display_name: str | None = Field(None, max_length=64)
    role: Literal["super_admin", "admin", "viewer"] | None = None
    is_active: bool | None = None


# ---------------- end users (admin side) ----------------
@router.get("/users", summary="微信用户列表")
def list_users(keyword: str | None = None, status: str | None = None, page: int = Query(1, ge=1),
               page_size: int = Query(20, ge=1, le=100), db: Session = Depends(get_db),
               _: AdminUser = Depends(require_role("viewer"))):
    q = select(User).where(User.deleted_at.is_(None))
    if keyword:
        q = q.where(User.nickname.contains(keyword))
    if status:
        q = q.where(User.status == status)
    total = db.scalar(select(func.count()).select_from(q.subquery())) or 0
    rows = list(db.scalars(q.order_by(User.id.desc()).offset((page - 1) * page_size).limit(page_size)))
    ids = [u.id for u in rows]
    conv_counts = dict(db.execute(select(Conversation.user_id, func.count(Conversation.id)).where(
        Conversation.user_id.in_(ids), Conversation.deleted_at.is_(None)).group_by(Conversation.user_id)).all()) if ids else {}
    tokens = dict(db.execute(select(UsageStatistic.user_id, func.sum(UsageStatistic.total_tokens)).where(
        UsageStatistic.user_id.in_(ids)).group_by(UsageStatistic.user_id)).all()) if ids else {}
    items = []
    for u in rows:
        d = UserOut.model_validate(u).model_dump(mode="json")
        d["conversation_count"] = conv_counts.get(u.id, 0)
        d["total_tokens"] = int(tokens.get(u.id) or 0)
        items.append(d)
    return ok({"items": items, "total": total, "page": page, "page_size": page_size})


@router.put("/users/{user_id}/status", summary="启用/禁用用户")
def set_status(user_id: int, body: UserStatusIn, request: Request, db: Session = Depends(get_db),
               admin: AdminUser = Depends(require_role("admin"))):
    u = db.get(User, user_id)
    if u is None or u.deleted_at is not None:
        raise NotFound("用户不存在")
    u.status = body.status
    db.commit()
    audit(db, admin, "set_status", "user", user_id, {"status": body.status}, request)
    return ok(UserOut.model_validate(u).model_dump(mode="json"))


# ---------------- end user self-service ----------------
@router.get("/users/me/usage", summary="当前小程序用户使用量")
def my_usage(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    since = date.today() - timedelta(days=29)
    row = db.execute(select(func.coalesce(func.sum(UsageStatistic.request_count), 0),
                            func.coalesce(func.sum(UsageStatistic.total_tokens), 0))
                     .where(UsageStatistic.user_id == user.id, UsageStatistic.stat_date >= since)).one()
    convs = db.scalar(select(func.count(Conversation.id)).where(Conversation.user_id == user.id,
                                                                Conversation.deleted_at.is_(None))) or 0
    return ok({"requests_30d": int(row[0]), "tokens_30d": int(row[1]), "conversations": convs})


# ---------------- admin accounts (super_admin) ----------------
@router.get("/admin-users", summary="管理员列表")
def list_admins(db: Session = Depends(get_db), _: AdminUser = Depends(require_role("super_admin"))):
    rows = db.scalars(select(AdminUser).where(AdminUser.deleted_at.is_(None)).order_by(AdminUser.id))
    return ok([AdminOut.model_validate(a).model_dump(mode="json") for a in rows])


@router.post("/admin-users", summary="新建管理员")
def create_admin(body: AdminCreateIn, request: Request, db: Session = Depends(get_db),
                 admin: AdminUser = Depends(require_role("super_admin"))):
    if db.scalar(select(AdminUser.id).where(AdminUser.username == body.username)):
        raise Conflict("用户名已存在")
    a = AdminUser(username=body.username, password_hash=hash_password(body.password),
                  display_name=body.display_name, role=body.role, is_active=True)
    db.add(a)
    db.commit()
    audit(db, admin, "create", "admin_user", a.id, {"username": a.username, "role": a.role}, request)
    return ok(AdminOut.model_validate(a).model_dump(mode="json"))


@router.put("/admin-users/{admin_id}", summary="修改管理员")
def update_admin(admin_id: int, body: AdminUpdateIn, request: Request, db: Session = Depends(get_db),
                 admin: AdminUser = Depends(require_role("super_admin"))):
    a = db.get(AdminUser, admin_id)
    if a is None or a.deleted_at is not None:
        raise NotFound("管理员不存在")
    if a.id == admin.id and (body.role not in (None, "super_admin") or body.is_active is False):
        raise BadRequest("不能降级或停用自己")
    if body.password:
        a.password_hash = hash_password(body.password)
    for k in ("display_name", "role", "is_active"):
        v = getattr(body, k)
        if v is not None:
            setattr(a, k, v)
    db.commit()
    audit(db, admin, "update", "admin_user", a.id, {"fields": sorted(body.model_dump(exclude_unset=True))}, request)
    return ok(AdminOut.model_validate(a).model_dump(mode="json"))
