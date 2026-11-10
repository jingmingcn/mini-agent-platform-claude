from fastapi import APIRouter, Depends, File, Query, Request, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import require_role
from app.core.response import ok
from app.models import AdminUser
from app.rag.retriever import retrieve
from app.schemas.knowledge import DocumentOut, KBCreate, KBUpdate, SearchIn
from app.services import knowledge_service as svc
from app.services.audit_service import audit

router = APIRouter(prefix="/knowledge-bases", tags=["知识库"])


@router.get("", summary="知识库列表")
def list_kbs(keyword: str | None = None, db: Session = Depends(get_db), _: AdminUser = Depends(require_role("viewer"))):
    return ok([svc.kb_to_out(db, kb) for kb in svc.list_kbs(db, keyword)])


@router.post("", summary="创建知识库")
def create_kb(body: KBCreate, request: Request, db: Session = Depends(get_db),
              admin: AdminUser = Depends(require_role("admin"))):
    kb = svc.create_kb(db, body, admin)
    audit(db, admin, "create", "knowledge_base", kb.id, {"name": kb.name}, request)
    return ok(svc.kb_to_out(db, kb))


@router.get("/{kb_id}", summary="知识库详情")
def get_kb(kb_id: int, db: Session = Depends(get_db), _: AdminUser = Depends(require_role("viewer"))):
    return ok(svc.kb_to_out(db, svc.get_kb_or_404(db, kb_id)))


@router.put("/{kb_id}", summary="修改知识库（切片/Embedding 变化后需重建）")
def update_kb(kb_id: int, body: KBUpdate, request: Request, db: Session = Depends(get_db),
              admin: AdminUser = Depends(require_role("admin"))):
    kb, needs_rebuild = svc.update_kb(db, svc.get_kb_or_404(db, kb_id), body)
    audit(db, admin, "update", "knowledge_base", kb.id, {"fields": sorted(body.model_dump(exclude_unset=True))}, request)
    return ok({**svc.kb_to_out(db, kb), "needs_rebuild": needs_rebuild})


@router.delete("/{kb_id}", summary="删除知识库（含向量数据）")
def delete_kb(kb_id: int, request: Request, db: Session = Depends(get_db),
              admin: AdminUser = Depends(require_role("admin"))):
    svc.delete_kb(db, svc.get_kb_or_404(db, kb_id))
    audit(db, admin, "delete", "knowledge_base", kb_id, None, request)
    return ok()


@router.post("/{kb_id}/documents", summary="上传文档（可多文件，异步解析）")
def upload(kb_id: int, request: Request, files: list[UploadFile] = File(...), db: Session = Depends(get_db),
           admin: AdminUser = Depends(require_role("admin"))):
    kb = svc.get_kb_or_404(db, kb_id)
    docs = svc.upload_documents(db, kb, files, admin)
    audit(db, admin, "upload", "document", ",".join(str(d.id) for d in docs),
          {"knowledge_base_id": kb.id, "files": [d.filename for d in docs]}, request)
    return ok([DocumentOut.model_validate(d).model_dump(mode="json") for d in docs])


@router.get("/{kb_id}/documents", summary="文档列表")
def list_docs(kb_id: int, status: str | None = None, keyword: str | None = None, page: int = Query(1, ge=1),
              page_size: int = Query(20, ge=1, le=100), db: Session = Depends(get_db),
              _: AdminUser = Depends(require_role("viewer"))):
    svc.get_kb_or_404(db, kb_id)
    rows, total = svc.list_documents(db, kb_id, status, keyword, page, page_size)
    return ok({"items": [DocumentOut.model_validate(d).model_dump(mode="json") for d in rows], "total": total,
               "page": page, "page_size": page_size})


@router.post("/{kb_id}/rebuild", summary="重建知识库向量索引")
def rebuild(kb_id: int, request: Request, db: Session = Depends(get_db),
            admin: AdminUser = Depends(require_role("admin"))):
    n = svc.rebuild_kb(db, svc.get_kb_or_404(db, kb_id))
    audit(db, admin, "rebuild", "knowledge_base", kb_id, {"documents": n}, request)
    return ok({"documents": n})


@router.post("/{kb_id}/search", summary="检索测试")
def search(kb_id: int, body: SearchIn, db: Session = Depends(get_db), _: AdminUser = Depends(require_role("viewer"))):
    kb = svc.get_kb_or_404(db, kb_id)
    hits = retrieve(db, [kb], body.query, top_k=body.top_k or kb.top_k,
                    score_threshold=body.score_threshold if body.score_threshold is not None else kb.score_threshold)
    return ok([h.to_citation(i, snippet_len=2000) for i, h in enumerate(hits, start=1)])
