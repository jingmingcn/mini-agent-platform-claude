from __future__ import annotations

import logging

from fastapi import Request
from sqlalchemy.orm import Session

from app.models import AdminUser, AuditLog

logger = logging.getLogger(__name__)
_SENSITIVE = {"api_key", "password", "password_hash", "api_key_encrypted", "secret"}


def _scrub(detail):
    if isinstance(detail, dict):
        return {k: ("***" if k in _SENSITIVE else _scrub(v)) for k, v in detail.items()}
    if isinstance(detail, list):
        return [_scrub(x) for x in detail]
    return detail


def audit(db: Session, admin: AdminUser | None, action: str, resource_type: str, resource_id=None,
          detail: dict | None = None, request: Request | None = None) -> None:
    ip = None
    if request is not None:
        fwd = request.headers.get("x-forwarded-for")
        ip = fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else None)
    db.add(AuditLog(admin_id=admin.id if admin else None, action=action, resource_type=resource_type,
                    resource_id=str(resource_id) if resource_id is not None else None,
                    detail=_scrub(detail) if detail else None, ip=ip))
    db.commit()
