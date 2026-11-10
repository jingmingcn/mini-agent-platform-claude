"""Builds providers from DB configs (decrypting keys server-side) and records call logs/usage."""
from __future__ import annotations

import logging
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.exceptions import BadRequest
from app.core.logging import redact
from app.core.security import decrypt_secret
from app.llm.base import BaseLLMProvider, TokenUsage
from app.llm.openai_compatible import OpenAICompatibleProvider
from app.models import ApiLog, LLMConfig, UsageStatistic

logger = logging.getLogger(__name__)

# Known OpenAI-compatible endpoints (admin can still enter any base_url).
PROVIDER_PRESETS = {
    "openai": {"label": "OpenAI", "base_url": "https://api.openai.com/v1", "chat_model": "gpt-4o-mini",
               "embedding_model": "text-embedding-3-small"},
    "deepseek": {"label": "DeepSeek", "base_url": "https://api.deepseek.com/v1", "chat_model": "deepseek-chat",
                 "embedding_model": None},
    "moonshot": {"label": "Moonshot (Kimi)", "base_url": "https://api.moonshot.cn/v1", "chat_model": "moonshot-v1-8k",
                 "embedding_model": None},
    "qwen": {"label": "通义千问 (DashScope)", "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
             "chat_model": "qwen-plus", "embedding_model": "text-embedding-v3"},
    "siliconflow": {"label": "SiliconFlow", "base_url": "https://api.siliconflow.cn/v1",
                    "chat_model": "deepseek-ai/DeepSeek-V3", "embedding_model": "BAAI/bge-m3"},
    "custom": {"label": "其他 OpenAI 兼容服务", "base_url": "", "chat_model": "", "embedding_model": ""},
}

# Test hook: tests may override to inject a fake provider.
_provider_factory = None


def set_provider_factory(factory) -> None:
    global _provider_factory
    _provider_factory = factory


def build_provider(cfg: LLMConfig) -> BaseLLMProvider:
    if _provider_factory is not None:
        return _provider_factory(cfg)
    return OpenAICompatibleProvider(
        api_key=decrypt_secret(cfg.api_key_encrypted),
        base_url=cfg.base_url,
        chat_model=cfg.chat_model,
        embedding_model=cfg.embedding_model,
        temperature=cfg.temperature,
        max_tokens=cfg.max_tokens,
        timeout=cfg.timeout_seconds or settings.LLM_TIMEOUT_SECONDS,
        max_retries=cfg.max_retries if cfg.max_retries is not None else settings.LLM_MAX_RETRIES,
        provider=cfg.provider,
    )


def get_default_config(db: Session) -> LLMConfig | None:
    q = select(LLMConfig).where(LLMConfig.deleted_at.is_(None), LLMConfig.enabled.is_(True))
    cfg = db.scalars(q.where(LLMConfig.is_default.is_(True))).first()
    return cfg or db.scalars(q.where(LLMConfig.chat_model.is_not(None)).order_by(LLMConfig.id)).first()


def resolve_chat_config(db: Session, llm_config_id: int | None) -> LLMConfig:
    cfg = None
    if llm_config_id:
        cfg = db.get(LLMConfig, llm_config_id)
        if cfg is None or cfg.deleted_at is not None:
            cfg = None
        elif not cfg.enabled:
            raise BadRequest("该智能体绑定的模型已被停用，请联系管理员")
    if cfg is None:
        cfg = get_default_config(db)
    if cfg is None:
        raise BadRequest("管理员尚未配置可用的大模型")
    if not cfg.chat_model:
        raise BadRequest("绑定的模型配置未设置 Chat Model")
    return cfg


def record_call(*, cfg: LLMConfig | None, call_type: str, usage: TokenUsage | None, latency_ms: int,
                status: str = "success", error: str | None = None, agent_id: int | None = None,
                user_id: int | None = None, conversation_id: int | None = None, model: str | None = None,
                db: Session | None = None) -> None:
    """Persist an api_logs row and bump daily usage. Uses its own session unless one is given.

    Never raises: logging failures must not break user requests.
    """
    own = db is None
    s = db or SessionLocal()
    try:
        u = usage or TokenUsage()
        s.add(ApiLog(llm_config_id=cfg.id if cfg else None, agent_id=agent_id, user_id=user_id,
                     conversation_id=conversation_id, call_type=call_type, provider=cfg.provider if cfg else "local",
                     model=model or (cfg.chat_model if cfg else None), prompt_tokens=u.prompt_tokens,
                     completion_tokens=u.completion_tokens, total_tokens=u.total_tokens, latency_ms=latency_ms,
                     status=status, error_message=redact(error)[:1000] if error else None))
        if call_type in ("chat", "stream") and status != "failed":
            today = date.today()
            cfg_id = cfg.id if cfg else None
            stat = s.scalars(select(UsageStatistic).where(
                UsageStatistic.stat_date == today, UsageStatistic.user_id.is_(None) if user_id is None else UsageStatistic.user_id == user_id,
                UsageStatistic.agent_id.is_(None) if agent_id is None else UsageStatistic.agent_id == agent_id,
                UsageStatistic.llm_config_id.is_(None) if cfg_id is None else UsageStatistic.llm_config_id == cfg_id,
            )).first()
            if stat is None:
                stat = UsageStatistic(stat_date=today, user_id=user_id, agent_id=agent_id, llm_config_id=cfg_id,
                                      request_count=0, prompt_tokens=0, completion_tokens=0, total_tokens=0)
                s.add(stat)
            stat.request_count += 1
            stat.prompt_tokens += u.prompt_tokens
            stat.completion_tokens += u.completion_tokens
            stat.total_tokens += u.total_tokens
        s.commit()
    except Exception:
        logger.exception("Failed to record LLM call log")
        s.rollback()
    finally:
        if own:
            s.close()
