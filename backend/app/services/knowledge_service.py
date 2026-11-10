from __future__ import annotations

from fastapi import UploadFile
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import utcnow
from app.core.exceptions import BadRequest, NotFound
from app.models import AdminUser, AgentKnowledgeBase, Document, DocumentChunk, KnowledgeBase, LLMConfig
from app.rag.pipeline import delete_document_vectors
from app.rag.vector_store import collection_for_kb, get_vector_store
from app.schemas.knowledge import KBCreate, KBOut, KBUpdate
from app.tasks.dispatcher import enqueue_document
from app.utils.files import KB_ALLOWED, read_and_validate, remove_file, sha256, store_bytes


def get_kb_or_404(db: Session, kb_id: int) -> KnowledgeBase:
    kb = db.get(KnowledgeBase, kb_id)
    if kb is None or kb.deleted_at is not None:
        raise NotFound("知识库不存在")
    return kb


def get_doc_or_404(db: Session, doc_id: int) -> Document:
    d = db.get(Document, doc_id)
    if d is None or d.deleted_at is not None:
        raise NotFound("文档不存在")
    return d


def kb_to_out(db: Session, kb: KnowledgeBase) -> dict:
    data = KBOut.model_validate(kb).model_dump(mode="json")
    data["document_count"] = db.scalar(select(func.count(Document.id)).where(
        Document.knowledge_base_id == kb.id, Document.deleted_at.is_(None))) or 0
    data["chunk_count"] = db.scalar(select(func.count(DocumentChunk.id)).where(
        DocumentChunk.knowledge_base_id == kb.id)) or 0
    return data


def _validate_embedding(db: Session, cfg_id: int | None) -> None:
    if cfg_id:
        cfg = db.get(LLMConfig, cfg_id)
        if cfg is None or cfg.deleted_at is not None:
            raise BadRequest("Embedding 模型配置不存在")
        if not cfg.embedding_model:
            raise BadRequest(f"模型配置「{cfg.name}」未设置 Embedding Model")


def list_kbs(db: Session, keyword: str | None = None) -> list[KnowledgeBase]:
    q = select(KnowledgeBase).where(KnowledgeBase.deleted_at.is_(None))
    if keyword:
        q = q.where(KnowledgeBase.name.contains(keyword))
    return list(db.scalars(q.order_by(KnowledgeBase.id.desc())))


def create_kb(db: Session, data: KBCreate, admin: AdminUser | None) -> KnowledgeBase:
    _validate_embedding(db, data.embedding_llm_config_id)
    kb = KnowledgeBase(**data.model_dump(), created_by=admin.id if admin else None)
    db.add(kb)
    db.flush()
    kb.collection_name = collection_for_kb(kb.id)
    db.commit()
    return kb


def update_kb(db: Session, kb: KnowledgeBase, data: KBUpdate) -> tuple[KnowledgeBase, bool]:
    patch = data.model_dump(exclude_unset=True)
    if "embedding_llm_config_id" in patch:
        _validate_embedding(db, patch["embedding_llm_config_id"])
    size = patch.get("chunk_size", kb.chunk_size)
    overlap = patch.get("chunk_overlap", kb.chunk_overlap)
    if overlap >= size:
        raise BadRequest("chunk_overlap 必须小于 chunk_size")
    needs_rebuild = any(k in patch and patch[k] != getattr(kb, k) for k in
                        ("embedding_llm_config_id", "embedding_model", "chunk_size", "chunk_overlap"))
    for k, v in patch.items():
        setattr(kb, k, v)
    db.commit()
    return kb, needs_rebuild


def delete_kb(db: Session, kb: KnowledgeBase) -> None:
    kb.deleted_at = utcnow()
    db.execute(delete(AgentKnowledgeBase).where(AgentKnowledgeBase.knowledge_base_id == kb.id))
    docs = list(db.scalars(select(Document).where(Document.knowledge_base_id == kb.id, Document.deleted_at.is_(None))))
    for d in docs:
        d.deleted_at = utcnow()
    db.execute(delete(DocumentChunk).where(DocumentChunk.knowledge_base_id == kb.id))
    db.commit()
    get_vector_store().delete_collection(collection_for_kb(kb.id))


def upload_documents(db: Session, kb: KnowledgeBase, files: list[UploadFile], admin: AdminUser | None) -> list[Document]:
    if not files:
        raise BadRequest("请选择要上传的文件")
    if len(files) > 20:
        raise BadRequest("单次最多上传 20 个文件")
    validated = [read_and_validate(f, KB_ALLOWED, settings.MAX_UPLOAD_MB) for f in files]  # all-or-nothing
    docs = []
    for data, filename, ext in validated:
        path = store_bytes(data, f"kb/{kb.id}", ext)
        doc = Document(knowledge_base_id=kb.id, filename=filename, file_type=ext, file_size=len(data),
                       storage_path=path, content_hash=sha256(data), status="pending", progress=0, stage="queued",
                       uploaded_by=admin.id if admin else None)
        db.add(doc)
        docs.append(doc)
    db.commit()
    for doc in docs:
        doc.task_id = enqueue_document(doc.id)
    db.commit()
    for doc in docs:
        db.refresh(doc)
    return docs


def list_documents(db: Session, kb_id: int, status: str | None = None, keyword: str | None = None,
                   page: int = 1, page_size: int = 20) -> tuple[list[Document], int]:
    q = select(Document).where(Document.knowledge_base_id == kb_id, Document.deleted_at.is_(None))
    if status:
        q = q.where(Document.status == status)
    if keyword:
        q = q.where(Document.filename.contains(keyword))
    total = db.scalar(select(func.count()).select_from(q.subquery())) or 0
    rows = list(db.scalars(q.order_by(Document.id.desc()).offset((page - 1) * page_size).limit(page_size)))
    return rows, total


def reparse(db: Session, doc: Document) -> Document:
    if doc.status == "processing":
        raise BadRequest("文档正在处理中")
    doc.status, doc.progress, doc.stage, doc.error_message = "pending", 0, "queued", None
    db.commit()
    doc.task_id = enqueue_document(doc.id)
    db.commit()
    db.refresh(doc)
    return doc


def rebuild_kb(db: Session, kb: KnowledgeBase) -> int:
    """Drop the whole collection (dimension may change) and re-process every document."""
    get_vector_store().delete_collection(collection_for_kb(kb.id))
    db.execute(delete(DocumentChunk).where(DocumentChunk.knowledge_base_id == kb.id))
    kb.embedding_dim = None
    docs = list(db.scalars(select(Document).where(Document.knowledge_base_id == kb.id, Document.deleted_at.is_(None))))
    for d in docs:
        d.status, d.progress, d.stage, d.error_message, d.chunk_count = "pending", 0, "queued", None, 0
    db.commit()
    for d in docs:
        d.task_id = enqueue_document(d.id)
    db.commit()
    return len(docs)


def delete_document(db: Session, doc: Document) -> None:
    delete_document_vectors(db, doc)
    doc.deleted_at = utcnow()
    db.commit()
    remove_file(doc.storage_path)


def list_chunks(db: Session, doc_id: int, page: int, page_size: int) -> tuple[list[DocumentChunk], int]:
    q = select(DocumentChunk).where(DocumentChunk.document_id == doc_id)
    total = db.scalar(select(func.count()).select_from(q.subquery())) or 0
    rows = list(db.scalars(q.order_by(DocumentChunk.chunk_index).offset((page - 1) * page_size).limit(page_size)))
    return rows, total
