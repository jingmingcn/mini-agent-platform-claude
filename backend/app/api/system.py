"""System settings, tools registry and public app config for the mini program."""
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent.tool_manager import tool_manager
from app.core.database import get_db
from app.core.permissions import get_principal, require_role
from app.core.response import ok
from app.models import AdminUser, SystemSetting
from app.services.audit_service import audit

router = APIRouter(tags=["系统"])

DEFAULT_SETTINGS = {
    "platform_name": "Mini-Agent 智能体平台",
    "welcome_text": "你好！选择一个智能体开始对话吧。",
    "quick_questions": ["你能做什么？", "帮我写一段自我介绍", "总结一下这份文档的要点"],
    "featured_agent_ids": [],
}


class SettingsIn(BaseModel):
    platform_name: str | None = Field(None, max_length=64)
    welcome_text: str | None = Field(None, max_length=500)
    quick_questions: list[str] | None = Field(None, max_length=10)
    featured_agent_ids: list[int] | None = None


def load_settings(db: Session) -> dict:
    data = dict(DEFAULT_SETTINGS)
    for row in db.scalars(select(SystemSetting)):
        data[row.key] = row.value
    return data


@router.get("/settings", summary="系统设置")
def get_settings(db: Session = Depends(get_db), _: AdminUser = Depends(require_role("viewer"))):
    return ok(load_settings(db))


@router.put("/settings", summary="更新系统设置")
def put_settings(body: SettingsIn, request: Request, db: Session = Depends(get_db),
                 admin: AdminUser = Depends(require_role("admin"))):
    for k, v in body.model_dump(exclude_unset=True).items():
        row = db.scalars(select(SystemSetting).where(SystemSetting.key == k)).first()
        if row is None:
            db.add(SystemSetting(key=k, value=v))
        else:
            row.value = v
    db.commit()
    audit(db, admin, "update", "settings", None, {"keys": sorted(body.model_dump(exclude_unset=True))}, request)
    return ok(load_settings(db))


@router.get("/tools", summary="已注册工具（插件）")
def list_tools(_: AdminUser = Depends(require_role("viewer"))):
    return ok([{"name": t.name, "description": t.description, "parameters": t.schema()["function"]["parameters"]}
               for t in tool_manager.list()])


@router.get("/app/config", summary="小程序首页配置（需登录）")
def app_config(db: Session = Depends(get_db), _=Depends(get_principal)):
    s = load_settings(db)
    return ok({k: s.get(k) for k in ("platform_name", "welcome_text", "quick_questions", "featured_agent_ids")})
