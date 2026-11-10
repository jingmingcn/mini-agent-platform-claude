from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db, utcnow
from app.core.exceptions import NotFound
from app.core.permissions import require_role
from app.core.response import ok
from app.models import AdminUser, AgentPrompt
from app.schemas.agent import PromptBase, PromptOut, PromptUpdate
from app.services.audit_service import audit

router = APIRouter(prefix="/prompts", tags=["Prompt 管理"])


def _get(db: Session, pid: int) -> AgentPrompt:
    p = db.get(AgentPrompt, pid)
    if p is None or p.deleted_at is not None:
        raise NotFound("Prompt 不存在")
    return p


@router.get("", summary="Prompt 模板列表；传 agent_id 返回该智能体的系统提示词历史版本")
def list_prompts(agent_id: int | None = None, db: Session = Depends(get_db),
                 _: AdminUser = Depends(require_role("viewer"))):
    q = select(AgentPrompt).where(AgentPrompt.deleted_at.is_(None))
    q = q.where(AgentPrompt.agent_id == agent_id, AgentPrompt.kind == "version") if agent_id else \
        q.where(AgentPrompt.kind == "template")
    rows = db.scalars(q.order_by(AgentPrompt.id.desc()))
    return ok([PromptOut.model_validate(r).model_dump(mode="json") for r in rows])


@router.post("", summary="新建 Prompt 模板")
def create_prompt(body: PromptBase, request: Request, db: Session = Depends(get_db),
                  admin: AdminUser = Depends(require_role("admin"))):
    p = AgentPrompt(**body.model_dump(), kind="template", version=1, created_by=admin.id)
    db.add(p)
    db.commit()
    audit(db, admin, "create", "prompt", p.id, {"name": p.name}, request)
    return ok(PromptOut.model_validate(p).model_dump(mode="json"))


@router.put("/{pid}", summary="修改 Prompt 模板（版本号 +1）")
def update_prompt(pid: int, body: PromptUpdate, request: Request, db: Session = Depends(get_db),
                  admin: AdminUser = Depends(require_role("admin"))):
    p = _get(db, pid)
    patch = body.model_dump(exclude_unset=True)
    for k, v in patch.items():
        setattr(p, k, v)
    if "content" in patch:
        p.version += 1
    db.commit()
    audit(db, admin, "update", "prompt", p.id, None, request)
    return ok(PromptOut.model_validate(p).model_dump(mode="json"))


@router.delete("/{pid}", summary="删除 Prompt")
def delete_prompt(pid: int, request: Request, db: Session = Depends(get_db),
                  admin: AdminUser = Depends(require_role("admin"))):
    p = _get(db, pid)
    p.deleted_at = utcnow()
    db.commit()
    audit(db, admin, "delete", "prompt", pid, None, request)
    return ok()
