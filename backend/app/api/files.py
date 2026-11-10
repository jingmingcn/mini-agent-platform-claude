from pathlib import Path

from fastapi import APIRouter, Depends, File, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import Forbidden, NotFound
from app.core.permissions import get_current_user
from app.core.response import ok
from app.core.security import sign_file_url, verify_file_sig
from app.models import UploadedFile, User
from app.rag.document_parser import ParseError, clean_text, parse_document
from app.utils.files import CHAT_ALLOWED, CHAT_IMAGE, read_and_validate, store_bytes

router = APIRouter(prefix="/files", tags=["文件"])

_MIME = {"png": "image/png", "jpg": "image/jpeg", "gif": "image/gif", "webp": "image/webp", "pdf": "application/pdf"}


def file_url(request: Request, f: UploadedFile) -> str:
    exp, sig = sign_file_url(f.id)
    return str(request.url_for("raw_file", file_id=f.id)) + f"?exp={exp}&sig={sig}"


@router.post("/upload", summary="小程序用户上传聊天附件（图片/文档）")
def upload(request: Request, file: UploadFile = File(...), db: Session = Depends(get_db),
           user: User = Depends(get_current_user)):
    data, filename, ext = read_and_validate(file, CHAT_ALLOWED, settings.MAX_CHAT_UPLOAD_MB)
    text = None
    if ext not in CHAT_IMAGE:
        try:
            text = clean_text("\n\n".join(p.text for p in parse_document(data, ext)))[:50_000]
        except ParseError as e:
            from app.core.exceptions import BadRequest
            raise BadRequest(f"文件解析失败: {e}") from e
    path = store_bytes(data, f"chat/{user.id}", ext)
    f = UploadedFile(user_id=user.id, filename=filename, file_type=ext, mime_type=_MIME.get(ext),
                     file_size=len(data), storage_path=path, extracted_text=text)
    db.add(f)
    db.commit()
    return ok({"id": f.id, "filename": f.filename, "file_type": f.file_type, "file_size": f.file_size,
               "url": file_url(request, f), "has_text": bool(text)})


@router.get("/{file_id}/url", summary="获取文件临时访问地址")
def get_url(file_id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    f = db.get(UploadedFile, file_id)
    if f is None or f.user_id != user.id:
        raise NotFound("文件不存在")
    return ok({"url": file_url(request, f)})


@router.get("/{file_id}/raw", name="raw_file", summary="下载文件（签名 URL，供 <image> 组件使用）")
def raw(file_id: int, exp: int, sig: str, db: Session = Depends(get_db)):
    if not verify_file_sig(file_id, exp, sig):
        raise Forbidden("链接已失效")
    f = db.get(UploadedFile, file_id)
    if f is None or not Path(f.storage_path).exists():
        raise NotFound("文件不存在")
    return FileResponse(f.storage_path, media_type=f.mime_type or "application/octet-stream", filename=f.filename)
