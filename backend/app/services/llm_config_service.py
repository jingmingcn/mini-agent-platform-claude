from __future__ import annotations

import time

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.database import utcnow
from app.core.exceptions import BadRequest, NotFound
from app.core.security import encrypt_secret
from app.llm.base import LLMError
from app.llm.provider_manager import build_provider, record_call
from app.models import Agent, KnowledgeBase, LLMConfig
from app.schemas.llm import LLMConfigCreate, LLMConfigOut, LLMConfigUpdate


def to_out(cfg: LLMConfig) -> dict:
    data = LLMConfigOut.model_validate({**{c: getattr(cfg, c) for c in LLMConfigOut.model_fields if hasattr(cfg, c)},
                                        "api_key_masked": f"****{cfg.api_key_last4}" if cfg.api_key_last4 else "****"})
    return data.model_dump(mode="json")


def get_or_404(db: Session, cfg_id: int) -> LLMConfig:
    cfg = db.get(LLMConfig, cfg_id)
    if cfg is None or cfg.deleted_at is not None:
        raise NotFound("模型配置不存在")
    return cfg


def list_configs(db: Session) -> list[LLMConfig]:
    return list(db.scalars(select(LLMConfig).where(LLMConfig.deleted_at.is_(None)).order_by(LLMConfig.id)))


def _clear_default(db: Session, except_id: int | None = None) -> None:
    q = update(LLMConfig).where(LLMConfig.is_default.is_(True))
    if except_id:
        q = q.where(LLMConfig.id != except_id)
    db.execute(q.values(is_default=False))


def create_config(db: Session, data: LLMConfigCreate) -> LLMConfig:
    key = data.api_key.strip()
    cfg = LLMConfig(**data.model_dump(exclude={"api_key", "base_url"}), base_url=str(data.base_url).rstrip("/"),
                    api_key_encrypted=encrypt_secret(key), api_key_last4=key[-4:])
    if not cfg.chat_model and not cfg.embedding_model:
        raise BadRequest("Chat Model 和 Embedding Model 至少配置一个")
    db.add(cfg)
    db.flush()
    if cfg.is_default:
        _clear_default(db, cfg.id)
    db.commit()
    return cfg


def update_config(db: Session, cfg: LLMConfig, data: LLMConfigUpdate) -> LLMConfig:
    patch = data.model_dump(exclude_unset=True)
    key = patch.pop("api_key", None)
    if key and key.strip():
        cfg.api_key_encrypted = encrypt_secret(key.strip())
        cfg.api_key_last4 = key.strip()[-4:]
        cfg.last_test_status = None
    if "base_url" in patch and patch["base_url"] is not None:
        patch["base_url"] = str(patch["base_url"]).rstrip("/")
    for k, v in patch.items():
        if k in ("chat_model", "embedding_model") and isinstance(v, str):
            v = v.strip() or None
        setattr(cfg, k, v)
    if cfg.is_default:
        _clear_default(db, cfg.id)
    db.commit()
    return cfg


def delete_config(db: Session, cfg: LLMConfig) -> None:
    used = db.scalar(select(Agent.id).where(Agent.llm_config_id == cfg.id, Agent.deleted_at.is_(None)).limit(1))
    if used:
        raise BadRequest("该模型配置仍被智能体使用，请先解绑")
    used_kb = db.scalar(select(KnowledgeBase.id).where(KnowledgeBase.embedding_llm_config_id == cfg.id,
                                                       KnowledgeBase.deleted_at.is_(None)).limit(1))
    if used_kb:
        raise BadRequest("该模型配置仍被知识库用于 Embedding，请先解绑")
    cfg.deleted_at = utcnow()
    cfg.is_default = False
    cfg.enabled = False
    db.commit()


def set_default(db: Session, cfg: LLMConfig) -> LLMConfig:
    if not cfg.enabled or not cfg.chat_model:
        raise BadRequest("只能将已启用且配置了 Chat Model 的模型设为默认")
    _clear_default(db)
    cfg.is_default = True
    db.commit()
    return cfg


def test_config(db: Session, cfg: LLMConfig) -> dict:
    provider = build_provider(cfg)
    t0 = time.time()
    try:
        result = provider.test_connection()
        cfg.last_test_status, cfg.last_test_message = "success", "连接成功"
        ok = True
    except LLMError as e:
        result = {"error": e.message}
        cfg.last_test_status, cfg.last_test_message = "failed", e.message[:500]
        ok = False
    finally:
        provider.close()
    latency = int((time.time() - t0) * 1000)
    db.commit()
    usage = None
    if ok and result.get("chat"):
        from app.llm.base import TokenUsage
        u = result["chat"]["usage"]
        usage = TokenUsage(u["prompt_tokens"], u["completion_tokens"], u["total_tokens"])
    record_call(cfg=cfg, call_type="test", usage=usage, latency_ms=latency, status="success" if ok else "failed",
                error=None if ok else result.get("error"))
    return {"success": ok, "latency_ms": latency, **result}
