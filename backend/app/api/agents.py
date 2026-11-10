from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import NotFound
from app.core.permissions import Principal, get_principal, require_role
from app.core.response import ok
from app.models import AdminUser
from app.schemas.agent import AgentCreate, AgentPermissionsIn, AgentPublicOut, AgentUpdate
from app.services import agent_service as svc
from app.services.agent_access import accessible_agent_ids, can_user_access_agent
from app.services.audit_service import audit

router = APIRouter(prefix="/agents", tags=["智能体"])


@router.get("", summary="智能体列表（管理员：全部；小程序用户：已发布且有权访问）")
def list_agents(keyword: str | None = None, status: str | None = None, db: Session = Depends(get_db),
                p: Principal = Depends(get_principal)):
    if p.is_admin:
        return ok([svc.to_out(db, a) for a in svc.list_agents(db, keyword=keyword, status=status)])
    allowed = accessible_agent_ids(db, p.id)
    agents = [a for a in svc.list_agents(db, keyword=keyword, status="published")
              if a.access_level == "public" or a.id in allowed]
    return ok([AgentPublicOut.model_validate(a).model_dump(mode="json") for a in agents])


@router.post("", summary="创建智能体")
def create_agent(body: AgentCreate, request: Request, db: Session = Depends(get_db),
                 admin: AdminUser = Depends(require_role("admin"))):
    a = svc.create_agent(db, body, admin)
    audit(db, admin, "create", "agent", a.id, {"name": a.name}, request)
    return ok(svc.to_out(db, a))


@router.get("/{agent_id}", summary="智能体详情")
def get_agent(agent_id: int, db: Session = Depends(get_db), p: Principal = Depends(get_principal)):
    a = svc.get_or_404(db, agent_id)
    if p.is_admin:
        return ok(svc.to_out(db, a))
    if a.status != "published" or not can_user_access_agent(db, p.id, a):
        raise NotFound("智能体不存在或未发布")
    return ok(AgentPublicOut.model_validate(a).model_dump(mode="json"))


@router.put("/{agent_id}", summary="编辑智能体")
def update_agent(agent_id: int, body: AgentUpdate, request: Request, db: Session = Depends(get_db),
                 admin: AdminUser = Depends(require_role("admin"))):
    a = svc.update_agent(db, svc.get_or_404(db, agent_id), body, admin)
    audit(db, admin, "update", "agent", a.id, {"fields": sorted(body.model_dump(exclude_unset=True))}, request)
    return ok(svc.to_out(db, a))


@router.delete("/{agent_id}", summary="删除智能体")
def delete_agent(agent_id: int, request: Request, db: Session = Depends(get_db),
                 admin: AdminUser = Depends(require_role("admin"))):
    svc.delete_agent(db, svc.get_or_404(db, agent_id))
    audit(db, admin, "delete", "agent", agent_id, None, request)
    return ok()


@router.post("/{agent_id}/publish", summary="发布智能体")
def publish(agent_id: int, request: Request, db: Session = Depends(get_db),
            admin: AdminUser = Depends(require_role("admin"))):
    a = svc.publish(db, svc.get_or_404(db, agent_id), True)
    audit(db, admin, "publish", "agent", a.id, None, request)
    return ok(svc.to_out(db, a))


@router.post("/{agent_id}/offline", summary="下线智能体")
def offline(agent_id: int, request: Request, db: Session = Depends(get_db),
            admin: AdminUser = Depends(require_role("admin"))):
    a = svc.publish(db, svc.get_or_404(db, agent_id), False)
    audit(db, admin, "offline", "agent", a.id, None, request)
    return ok(svc.to_out(db, a))


@router.get("/{agent_id}/permissions", summary="受限智能体的授权用户")
def get_permissions(agent_id: int, db: Session = Depends(get_db), _: AdminUser = Depends(require_role("viewer"))):
    svc.get_or_404(db, agent_id)
    return ok(svc.get_permissions(db, agent_id))


@router.put("/{agent_id}/permissions", summary="设置授权用户（覆盖）")
def set_permissions(agent_id: int, body: AgentPermissionsIn, request: Request, db: Session = Depends(get_db),
                    admin: AdminUser = Depends(require_role("admin"))):
    svc.get_or_404(db, agent_id)
    svc.set_permissions(db, agent_id, body.user_ids)
    audit(db, admin, "set_permissions", "agent", agent_id, {"user_count": len(body.user_ids)}, request)
    return ok(svc.get_permissions(db, agent_id))
