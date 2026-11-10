from __future__ import annotations

import app.models  # noqa: F401  (register mappers in worker process)
from app.rag.pipeline import process_document
from app.tasks.celery_app import celery_app


@celery_app.task(name="documents.process", bind=True, max_retries=2, default_retry_delay=10)
def process_document_task(self, document_id: int) -> dict:
    return process_document(document_id)
