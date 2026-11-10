"""Dispatch background jobs to Celery, or to an in-process thread pool when Celery is disabled.

The in-process mode keeps local development dependency-free (and is required when Qdrant runs in
embedded mode, because the embedded store cannot be shared across processes).
"""
from __future__ import annotations

import logging
import uuid
from concurrent.futures import ThreadPoolExecutor

from app.core.config import settings

logger = logging.getLogger(__name__)
_pool: ThreadPoolExecutor | None = None
# Tests set this to True to run jobs synchronously.
RUN_SYNC = False


def _get_pool() -> ThreadPoolExecutor:
    global _pool
    if _pool is None:
        _pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="doc-worker")
    return _pool


def enqueue_document(document_id: int) -> str:
    from app.rag.pipeline import process_document

    if RUN_SYNC:
        process_document(document_id)
        return "sync"
    if settings.CELERY_ENABLED:
        from app.tasks.document_tasks import process_document_task

        res = process_document_task.delay(document_id)
        return res.id
    task_id = f"local-{uuid.uuid4().hex[:12]}"
    _get_pool().submit(process_document, document_id)
    return task_id
