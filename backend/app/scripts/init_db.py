"""Initialise database: (optionally) create tables, seed super admin, settings, demo KB and default agents.

Usage:
    python -m app.scripts.init_db            # seed only (run `alembic upgrade head` first)
    python -m app.scripts.init_db --create   # create tables via metadata (dev / SQLite)

Optional env to seed a default model:  SEED_LLM_PROVIDER, SEED_LLM_BASE_URL, SEED_LLM_API_KEY,
SEED_LLM_CHAT_MODEL, SEED_LLM_EMBEDDING_MODEL
"""
from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path

from sqlalchemy import select

import app.models  # noqa: F401
from app.core.config import settings
from app.core.database import Base, SessionLocal, engine
from app.core.logging import setup_logging
from app.core.security import encrypt_secret, hash_password
from app.models import Agent, AgentKnowledgeBase, AdminUser, Document, KnowledgeBase, LLMConfig, SystemSetting
from app.rag.pipeline import process_document
from app.utils.files import sha256, store_bytes

logger = logging.getLogger("init_db")
DEMO_DOC = Path(__file__).parent / "demo" / "platform_guide.md"


def seed(db) -> None:
    admin = db.scalars(select(AdminUser).where(AdminUser.username == settings.ADMIN_USERNAME)).first()
    if admin is None:
        admin = AdminUser(username=settings.ADMIN_USERNAME, password_hash=hash_password(settings.ADMIN_PASSWORD),
                          display_name="超级管理员", role="super_admin", is_active=True)
        db.add(admin)
        db.commit()
        logger.info("Created super admin '%s'", admin.username)

    for key, value in {"platform_name": "Mini-Agent 智能体平台",
                       "welcome_text": "你好！我是你的 AI 助手，选择一个智能体开始对话吧。",
                       "quick_questions": ["平台支持哪些大模型？", "如何创建知识库？", "什么是拒答策略？"]}.items():
        if not db.scalars(select(SystemSetting).where(SystemSetting.key == key)).first():
            db.add(SystemSetting(key=key, value=value))
    db.commit()

    api_key = os.getenv("SEED_LLM_API_KEY")
    if api_key and not db.scalars(select(LLMConfig).where(LLMConfig.deleted_at.is_(None))).first():
        from app.llm.provider_manager import PROVIDER_PRESETS
        provider = os.getenv("SEED_LLM_PROVIDER", "deepseek")
        preset = PROVIDER_PRESETS.get(provider, PROVIDER_PRESETS["custom"])
        cfg = LLMConfig(name=f"{preset['label']} (seed)", provider=provider,
                        base_url=os.getenv("SEED_LLM_BASE_URL") or preset["base_url"],
                        api_key_encrypted=encrypt_secret(api_key), api_key_last4=api_key[-4:],
                        chat_model=os.getenv("SEED_LLM_CHAT_MODEL") or preset["chat_model"],
                        embedding_model=os.getenv("SEED_LLM_EMBEDDING_MODEL") or preset["embedding_model"],
                        temperature=0.7, enabled=True, is_default=True)
        db.add(cfg)
        db.commit()
        logger.info("Seeded default LLM config for provider %s", provider)

    kb = db.scalars(select(KnowledgeBase).where(KnowledgeBase.name == "平台使用手册",
                                                KnowledgeBase.deleted_at.is_(None))).first()
    if kb is None:
        kb = KnowledgeBase(name="平台使用手册", description="演示知识库：平台功能说明（local-hash 离线向量化）",
                           category="演示", chunk_size=300, chunk_overlap=50, top_k=4, score_threshold=0.15,
                           created_by=admin.id)
        db.add(kb)
        db.flush()
        kb.collection_name = f"kb_{kb.id}"
        data = DEMO_DOC.read_bytes()
        doc = Document(knowledge_base_id=kb.id, filename="平台使用手册.md", file_type="md", file_size=len(data),
                       storage_path=store_bytes(data, f"kb/{kb.id}", "md"), content_hash=sha256(data),
                       status="pending", uploaded_by=admin.id)
        db.add(doc)
        db.commit()
        result = process_document(doc.id)
        logger.info("Demo document processed: %s", result)

    if not db.scalars(select(Agent).where(Agent.name == "通用助手", Agent.deleted_at.is_(None))).first():
        db.add(Agent(name="通用助手", description="通用 AI 对话助手，可以回答各类问题、写作和编程。", avatar="🤖",
                     category="通用", system_prompt="你是一个专业、友好、严谨的 AI 助手。回答要准确、有条理。",
                     welcome_message="你好，我是通用助手，有什么可以帮你？",
                     suggested_questions=["帮我写一封请假邮件", "解释一下什么是 RAG", "用 Python 写一个快速排序"],
                     enable_memory=True, status="published", access_level="public", is_featured=True,
                     sort_order=10, created_by=admin.id))
        db.commit()

    helper = db.scalars(select(Agent).where(Agent.name == "平台助手", Agent.deleted_at.is_(None))).first()
    if helper is None:
        helper = Agent(name="平台助手", description="基于「平台使用手册」知识库回答平台使用问题。", avatar="📘",
                       category="知识库问答",
                       system_prompt="你是 Mini-Agent 平台的使用顾问，请依据知识库资料回答平台使用相关问题，回答简洁并标注引用。",
                       welcome_message="你好，我可以解答 Mini-Agent 平台的使用问题。",
                       suggested_questions=["如何添加大模型？", "文档处理失败怎么办？", "什么是拒答策略？"],
                       enable_rag=True, rag_top_k=4, rag_score_threshold=0.15, rag_no_result_policy="fallback",
                       enable_memory=True, status="published", access_level="public", is_featured=True,
                       sort_order=9, created_by=admin.id)
        db.add(helper)
        db.flush()
        db.add(AgentKnowledgeBase(agent_id=helper.id, knowledge_base_id=kb.id))
        db.commit()
    logger.info("Seed complete.")


def main() -> None:
    setup_logging()
    parser = argparse.ArgumentParser()
    parser.add_argument("--create", action="store_true", help="create tables from metadata (dev only)")
    args = parser.parse_args()
    if args.create:
        Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        seed(db)
    finally:
        db.close()
        from app.rag.vector_store import get_vector_store
        get_vector_store().close()


if __name__ == "__main__":
    main()
