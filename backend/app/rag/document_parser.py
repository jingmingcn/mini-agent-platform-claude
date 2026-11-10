"""Parse uploaded documents into page-aware plain text, with resource limits.

Document content is treated as *untrusted data* everywhere downstream.
"""
from __future__ import annotations

import csv
import io
import re
import zipfile
from dataclasses import dataclass

from app.core.config import settings


class ParseError(Exception):
    pass


@dataclass
class ParsedPage:
    text: str
    page_number: int | None = None


def _decode(data: bytes) -> str:
    for enc in ("utf-8-sig", "gb18030", "big5"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _parse_pdf(data: bytes) -> list[ParsedPage]:
    from pypdf import PdfReader

    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except Exception as e:
                raise ParseError("PDF 已加密，无法解析") from e
        n = len(reader.pages)
    except ParseError:
        raise
    except Exception as e:
        raise ParseError(f"PDF 文件损坏或格式不支持: {e}") from e
    if n > settings.MAX_PDF_PAGES:
        raise ParseError(f"PDF 页数 {n} 超过上限 {settings.MAX_PDF_PAGES}")
    pages = []
    for i, page in enumerate(reader.pages, start=1):
        try:
            txt = page.extract_text() or ""
        except Exception:
            txt = ""
        pages.append(ParsedPage(txt, i))
    if not any(p.text.strip() for p in pages):
        raise ParseError("PDF 中未提取到文本（可能是扫描件，OCR 暂未支持）")
    return pages


def _check_zip(data: bytes) -> None:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            total = sum(i.file_size for i in zf.infolist())
            if total > 200 * 1024 * 1024:
                raise ParseError("DOCX 解压后体积过大，疑似压缩炸弹")
            if "word/document.xml" not in zf.namelist():
                raise ParseError("不是有效的 DOCX 文件")
    except zipfile.BadZipFile as e:
        raise ParseError("DOCX 文件损坏") from e


def _parse_docx(data: bytes) -> list[ParsedPage]:
    import docx

    _check_zip(data)
    try:
        d = docx.Document(io.BytesIO(data))
    except Exception as e:
        raise ParseError(f"DOCX 解析失败: {e}") from e
    lines: list[str] = []
    for block in d.element.body.iterchildren():
        tag = block.tag.rsplit("}", 1)[-1]
        if tag == "p":
            text = "".join(t.text or "" for t in block.iter() if t.tag.endswith("}t"))
            if text.strip():
                lines.append(text)
        elif tag == "tbl":
            for row in block.iter():
                if row.tag.endswith("}tr"):
                    cells = []
                    for cell in row.iterchildren():
                        if cell.tag.endswith("}tc"):
                            cells.append("".join(t.text or "" for t in cell.iter() if t.tag.endswith("}t")).strip())
                    if any(cells):
                        lines.append(" | ".join(cells))
    return [ParsedPage("\n".join(lines))]


def _parse_html(data: bytes) -> list[ParsedPage]:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(_decode(data), "html.parser")
    for tag in soup(["script", "style", "noscript", "iframe", "svg", "head"]):
        tag.decompose()
    text = soup.get_text("\n")
    return [ParsedPage(text)]


def _parse_csv(data: bytes) -> list[ParsedPage]:
    text = _decode(data)
    try:
        dialect = csv.Sniffer().sniff(text[:4096])
    except csv.Error:
        dialect = csv.excel
    reader = csv.reader(io.StringIO(text), dialect)
    rows = list(reader)
    if not rows:
        return [ParsedPage("")]
    header = rows[0]
    lines = []
    for r in rows[1:]:
        pairs = [f"{h.strip()}: {v.strip()}" for h, v in zip(header, r) if v and v.strip()]
        if pairs:
            lines.append("；".join(pairs))
    if not lines:  # single-row / headerless
        lines = [", ".join(r) for r in rows]
    return [ParsedPage("\n\n".join(lines))]


def parse_document(data: bytes, file_type: str) -> list[ParsedPage]:
    ft = file_type.lower()
    if ft == "pdf":
        pages = _parse_pdf(data)
    elif ft == "docx":
        pages = _parse_docx(data)
    elif ft in ("html", "htm"):
        pages = _parse_html(data)
    elif ft == "csv":
        pages = _parse_csv(data)
    elif ft in ("txt", "md", "markdown"):
        pages = [ParsedPage(_decode(data))]
    else:
        raise ParseError(f"不支持的文件类型: {file_type}")
    total = sum(len(p.text) for p in pages)
    if total > settings.MAX_PARSE_CHARS:
        raise ParseError(f"文档文本量 {total} 字符超过上限 {settings.MAX_PARSE_CHARS}")
    return pages


_WS = re.compile(r"[ \t 　]+")
_MULTI_NL = re.compile(r"\n{3,}")
_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def clean_text(text: str) -> str:
    text = _CTRL.sub("", text.replace("\r\n", "\n").replace("\r", "\n"))
    text = "\n".join(_WS.sub(" ", line).strip() for line in text.split("\n"))
    return _MULTI_NL.sub("\n\n", text).strip()
