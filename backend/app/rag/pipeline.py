"""Document ingestion pipeline: file -> parse -> clean -> chunk -> embed -> vector store."""
from __future__ import annotations

import logging
import uuid
from pathlib import Path

from sqlalchemy import delete, select

from app.core.database import SessionLocal, utcnow
from app.models import Document, DocumentChunk, KnowledgeBase
from app.rag.document_parser import ParseError, clean_text, parse_document
from app.rag.embedding import get_embedder
from app.rag.text_splitter import RecursiveTextSplitter
from app.rag.vector_store import VectorRecord, collection_for_kb, get_vector_store

logger = logging.getLogger(__name__)
EMBED_BATCH = 32


def _set(db, doc: Document, **fields) -> None:
    for k, v in fields.items():
        setattr(doc, k, v)
    db.commit()


def delete_document_vectors(db, doc: Document) -> None:
    get_vector_store().delete_by_filter(collection_for_kb(doc.knowledge_base_id), {"document_id": doc.id})
    db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == doc.id))
    doc.chunk_count = 0
    db.commit()


def process_document(document_id: int) -> dict:
    """Idempotent: re-running replaces previous chunks/vectors of the document."""
    db = SessionLocal()
    try:
        doc = db.get(Document, document_id)
        if doc is None or doc.deleted_at is not None:
            return {"status": "skipped", "reason": "document not found"}
        kb = db.get(KnowledgeBase, doc.knowledge_base_id)
        if kb is None or kb.deleted_at is not None:
            _set(db, doc, status="failed", error_message="知识库不存在")
            return {"status": "failed"}
        _set(db, doc, status="processing", progress=5, stage="parsing", error_message=None)

        try:
            data = Path(doc.storage_path).read_bytes()
        except OSError as e:
            raise ParseError(f"读取文件失败: {e}") from e
        pages = parse_document(data, doc.file_type)
        _set(db, doc, progress=20, stage="cleaning")
        cleaned = [(clean_text(p.text), p.page_number) for p in pages]
        char_count = sum(len(t) for t, _ in cleaned)
        if char_count == 0:
            raise ParseError("文档中没有可用的文本内容")

        _set(db, doc, progress=30, stage="chunking", char_count=char_count)
        splitter = RecursiveTextSplitter(kb.chunk_size, min(kb.chunk_overlap, kb.chunk_size - 1))
        chunks = splitter.split_pages(cleaned)

        # Replace previous data (re-parse / rebuild)
        delete_document_vectors(db, doc)

        _set(db, doc, progress=40, stage="embedding")
        embedder = get_embedder(db, kb)
        store = get_vector_store()
        collection = collection_for_kb(kb.id)
        rows: list[DocumentChunk] = []
        total = len(chunks)
        for start in range(0, total, EMBED_BATCH):
            batch = chunks[start:start + EMBED_BATCH]
            vectors = embedder.embed([c.content for c in batch])
            if start == 0:
                dim = len(vectors[0])
                if kb.embedding_dim and kb.embedding_dim != dim:
                    has_other = db.scalar(select(DocumentChunk.id).where(
                        DocumentChunk.knowledge_base_id == kb.id, DocumentChunk.document_id != doc.id).limit(1))
                    if has_other:
                        raise ParseError(f"Embedding 维度从 {kb.embedding_dim} 变为 {dim}，请先执行知识库重建")
                    store.delete_collection(collection)
                store.ensure_collection(collection, dim)
                kb.embedding_dim = dim
                kb.collection_name = collection
                db.commit()
            records = []
            for c, vec in zip(batch, vectors):
                cid = str(uuid.uuid4())
                meta = {"filename": doc.filename, "file_type": doc.file_type}
                records.append(VectorRecord(id=cid, vector=vec, payload={
                    "chunk_id": cid, "document_id": doc.id, "knowledge_base_id": kb.id,
                    "chunk_index": c.index, "page_number": c.page_number, "content": c.content, "metadata": meta}))
                rows.append(DocumentChunk(chunk_id=cid, document_id=doc.id, knowledge_base_id=kb.id,
                                          chunk_index=c.index, content=c.content, char_count=len(c.content),
                                          page_number=c.page_number, meta=meta))
            store.upsert(collection, records)
            progress = 40 + int(55 * min(start + EMBED_BATCH, total) / max(total, 1))
            _set(db, doc, progress=progress)

        db.add_all(rows)
        _set(db, doc, status="completed", progress=100, stage="done", chunk_count=len(rows), updated_at=utcnow())
        logger.info("Document %s processed: %s chunks", doc.id, len(rows))
        return {"status": "completed", "chunks": len(rows)}
    except Exception as e:
        db.rollback()
        logger.warning("Document %s processing failed: %s", document_id, e)
        doc = db.get(Document, document_id)
        if doc is not None:
            msg = e.message if hasattr(e, "message") else str(e)
            _set(db, doc, status="failed", stage="failed", error_message=str(msg)[:2000])
        return {"status": "failed", "error": str(e)}
    finally:
        db.close()
