"""Upload validation and storage helpers."""
from __future__ import annotations

import hashlib
import os
import re
import uuid
from pathlib import Path

from fastapi import UploadFile

from app.core.config import settings
from app.core.exceptions import BadRequest

KB_ALLOWED = {"pdf", "docx", "txt", "md", "markdown", "html", "htm", "csv"}
CHAT_IMAGE = {"png", "jpg", "jpeg", "gif", "webp"}
CHAT_ALLOWED = KB_ALLOWED | CHAT_IMAGE

_MAGIC = {
    "pdf": [b"%PDF"],
    "docx": [b"PK\x03\x04"],
    "png": [b"\x89PNG"],
    "jpg": [b"\xff\xd8\xff"],
    "jpeg": [b"\xff\xd8\xff"],
    "gif": [b"GIF8"],
    "webp": [b"RIFF"],
}


def safe_filename(name: str) -> str:
    name = os.path.basename(name or "file").replace("\x00", "")
    name = re.sub(r"[\\/:*?\"<>|\r\n\t]", "_", name).strip() or "file"
    return name[:200]


def ext_of(name: str) -> str:
    return name.rsplit(".", 1)[-1].lower() if "." in name else ""


def read_and_validate(upload: UploadFile, allowed: set[str], max_mb: int) -> tuple[bytes, str, str]:
    """Read the upload fully (bounded), validate extension, size and magic bytes."""
    filename = safe_filename(upload.filename or "")
    ext = ext_of(filename)
    if ext not in allowed:
        raise BadRequest(f"不支持的文件类型: .{ext or '?'}，允许: {', '.join(sorted(allowed))}")
    limit = max_mb * 1024 * 1024
    data = upload.file.read(limit + 1)
    if len(data) > limit:
        raise BadRequest(f"文件超过大小限制 {max_mb}MB")
    if not data:
        raise BadRequest("文件为空")
    magics = _MAGIC.get(ext)
    if magics and not any(data.startswith(m) for m in magics):
        raise BadRequest("文件内容与扩展名不匹配")
    if ext in {"txt", "md", "markdown", "csv", "html", "htm"} and b"\x00" in data[:4096]:
        raise BadRequest("文本文件包含二进制内容")
    if ext == "md" or ext == "markdown":
        ext = "md"
    if ext == "htm":
        ext = "html"
    if ext == "jpeg":
        ext = "jpg"
    return data, filename, ext


def store_bytes(data: bytes, subdir: str, ext: str) -> str:
    root = Path(settings.UPLOAD_DIR) / subdir
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{uuid.uuid4().hex}.{ext}"
    path.write_bytes(data)
    return str(path)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def remove_file(path: str | None) -> None:
    if path:
        try:
            Path(path).unlink(missing_ok=True)
        except OSError:
            pass
