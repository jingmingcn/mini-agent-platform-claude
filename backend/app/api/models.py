from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import require_role
from app.core.response import ok
from app.llm.provider_manager import PROVIDER_PRESETS
from app.models import AdminUser
from app.schemas.llm import LLMConfigCreate, LLMConfigUpdate
from app.services import llm_config_service as svc
from app.services.audit_service import audit

router = APIRouter(prefix="/models", tags=["大模型配置"])


@router.get("/providers", summary="内置 Provider 预设")
def providers(_: AdminUser = Depends(require_role("viewer"))):
    return ok([{"provider": k, **v} for k, v in PROVIDER_PRESETS.items()])


@router.get("", summary="模型配置列表（不返回 API Key）")
def list_models(db: Session = Depends(get_db), _: AdminUser = Depends(require_role("viewer"))):
    return ok([svc.to_out(c) for c in svc.list_configs(db)])


@router.post("", summary="新增模型配置")
def create_model(body: LLMConfigCreate, request: Request, db: Session = Depends(get_db),
                 admin: AdminUser = Depends(require_role("admin"))):
    cfg = svc.create_config(db, body)
    audit(db, admin, "create", "llm_config", cfg.id, {"name": cfg.name, "provider": cfg.provider}, request)
    return ok(svc.to_out(cfg))


@router.get("/{cfg_id}", summary="模型配置详情")
def get_model(cfg_id: int, db: Session = Depends(get_db), _: AdminUser = Depends(require_role("viewer"))):
    return ok(svc.to_out(svc.get_or_404(db, cfg_id)))


@router.put("/{cfg_id}", summary="修改模型配置（api_key 留空不修改）")
def update_model(cfg_id: int, body: LLMConfigUpdate, request: Request, db: Session = Depends(get_db),
                 admin: AdminUser = Depends(require_role("admin"))):
    cfg = svc.update_config(db, svc.get_or_404(db, cfg_id), body)
    audit(db, admin, "update", "llm_config", cfg.id,
          {"fields": sorted(body.model_dump(exclude_unset=True).keys())}, request)
    return ok(svc.to_out(cfg))


@router.delete("/{cfg_id}", summary="删除模型配置")
def delete_model(cfg_id: int, request: Request, db: Session = Depends(get_db),
                 admin: AdminUser = Depends(require_role("admin"))):
    svc.delete_config(db, svc.get_or_404(db, cfg_id))
    audit(db, admin, "delete", "llm_config", cfg_id, None, request)
    return ok()


@router.post("/{cfg_id}/test", summary="测试模型连接")
def test_model(cfg_id: int, db: Session = Depends(get_db), _: AdminUser = Depends(require_role("admin"))):
    return ok(svc.test_config(db, svc.get_or_404(db, cfg_id)))


@router.post("/{cfg_id}/default", summary="设为默认模型")
def set_default(cfg_id: int, request: Request, db: Session = Depends(get_db),
                admin: AdminUser = Depends(require_role("admin"))):
    cfg = svc.set_default(db, svc.get_or_404(db, cfg_id))
    audit(db, admin, "set_default", "llm_config", cfg.id, None, request)
    return ok(svc.to_out(cfg))
