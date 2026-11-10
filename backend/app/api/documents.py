from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import require_role
from app.core.response import ok
from app.models import AdminUser
from app.rag.pipeline import delete_document_vectors
from app.schemas.knowledge import ChunkOut, DocumentOut
from app.services import knowledge_service as svc
from app.services.audit_service import audit

router = APIRouter(prefix="/documents", tags=["文档"])


@router.get("/{doc_id}", summary="文档详情（含处理状态/失败原因）")
def get_doc(doc_id: int, db: Session = Depends(get_db), _: AdminUser = Depends(require_role("viewer"))):
    return ok(DocumentOut.model_validate(svc.get_doc_or_404(db, doc_id)).model_dump(mode="json"))


@router.get("/{doc_id}/chunks", summary="文档切片结果")
def chunks(doc_id: int, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
           db: Session = Depends(get_db), _: AdminUser = Depends(require_role("viewer"))):
    svc.get_doc_or_404(db, doc_id)
    rows, total = svc.list_chunks(db, doc_id, page, page_size)
    return ok({"items": [ChunkOut.model_validate(c).model_dump(mode="json") for c in rows], "total": total,
               "page": page, "page_size": page_size})


@router.post("/{doc_id}/reparse", summary="重新解析文档")
def reparse(doc_id: int, request: Request, db: Session = Depends(get_db),
            admin: AdminUser = Depends(require_role("admin"))):
    doc = svc.reparse(db, svc.get_doc_or_404(db, doc_id))
    audit(db, admin, "reparse", "document", doc_id, None, request)
    return ok(DocumentOut.model_validate(doc).model_dump(mode="json"))


@router.delete("/{doc_id}/vectors", summary="删除文档的向量数据（保留文件）")
def delete_vectors(doc_id: int, request: Request, db: Session = Depends(get_db),
                   admin: AdminUser = Depends(require_role("admin"))):
    doc = svc.get_doc_or_404(db, doc_id)
    delete_document_vectors(db, doc)
    doc.status, doc.stage, doc.progress = "pending", "vectors_deleted", 0
    db.commit()
    audit(db, admin, "delete_vectors", "document", doc_id, None, request)
    return ok(DocumentOut.model_validate(doc).model_dump(mode="json"))


@router.delete("/{doc_id}", summary="删除文档（文件+切片+向量）")
def delete_doc(doc_id: int, request: Request, db: Session = Depends(get_db),
               admin: AdminUser = Depends(require_role("admin"))):
    svc.delete_document(db, svc.get_doc_or_404(db, doc_id))
    audit(db, admin, "delete", "document", doc_id, None, request)
    return ok()
