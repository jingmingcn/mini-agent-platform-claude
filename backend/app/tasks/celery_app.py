"""Celery application. Start a worker with:  celery -A app.tasks.celery_app worker -l info"""
from __future__ import annotations

from celery import Celery

from app.core.config import settings
from app.core.logging import setup_logging

setup_logging(settings.DEBUG)

celery_app = Celery(
    "mini_agent",
    broker=settings.broker_url,
    backend=settings.CELERY_RESULT_BACKEND or settings.broker_url,
    include=["app.tasks.document_tasks"],
)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_time_limit=60 * 30,
    task_soft_time_limit=60 * 25,
    result_expires=3600 * 24,
    timezone="Asia/Shanghai",
)
