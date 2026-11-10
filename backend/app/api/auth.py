from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import Principal, get_principal
from app.core.response import ok
from app.schemas.auth import AdminLoginIn, AdminOut, UserOut, WechatLoginIn
from app.services import auth_service
from app.services.audit_service import audit

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/admin/login", summary="管理员登录")
def admin_login(body: AdminLoginIn, request: Request, db: Session = Depends(get_db)):
    data = auth_service.admin_login(db, body.username, body.password)
    from app.models import AdminUser
    audit(db, db.get(AdminUser, data["profile"]["id"]), "login", "admin_user", data["profile"]["id"], request=request)
    return ok(data)


@router.post("/wechat/login", summary="微信小程序登录 (wx.login code)")
def wechat_login(body: WechatLoginIn, db: Session = Depends(get_db)):
    return ok(auth_service.wechat_login(db, body.code, body.nickname, body.avatar_url, body.dev_openid))


@router.get("/me", summary="当前登录身份")
def me(p: Principal = Depends(get_principal)):
    if p.is_admin:
        return ok({"principal_type": "admin", "profile": AdminOut.model_validate(p.admin).model_dump(mode="json")})
    return ok({"principal_type": "user", "profile": UserOut.model_validate(p.user).model_dump(mode="json")})
