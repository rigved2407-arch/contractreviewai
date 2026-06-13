import os
import tempfile
from pathlib import Path
from typing import Optional

import fitz
from docx import Document


def parse_document(file_path: str) -> Optional[str]:
    ext = Path(file_path).suffix.lower()
    if ext == ".pdf":
        return _parse_pdf(file_path)
    elif ext == ".docx":
        return _parse_docx(file_path)
    elif ext == ".doc":
        return _parse_docx(file_path)
    return None


def _parse_pdf(file_path: str) -> str:
    text_parts = []
    with fitz.open(file_path) as doc:
        for page in doc:
            text_parts.append(page.get_text())
    return "\n\n".join(text_parts)


def _parse_docx(file_path: str) -> str:
    doc = Document(file_path)
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n\n".join(paragraphs)


def parse_document_raw(content: bytes, ext: str) -> Optional[str]:
    suffix = ext if ext.startswith(".") else "." + ext
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name
    try:
        return parse_document(tmp_path)
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


def get_section_structure(text: str) -> list[dict]:
    import re
    sections = []
    current_section = {"header": "Preamble", "content": []}
    section_pattern = re.compile(
        r'^(?:\d+\.?\s*|\([a-z]\)\s*|[A-Z][A-Z\s]+|[A-Z][a-z]+(?:[\s-][A-Z][a-z]+)*)',
        re.MULTILINE
    )

    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        if section_pattern.match(line) and len(line) < 200:
            if current_section["content"]:
                sections.append(current_section)
            current_section = {"header": line, "content": []}
        else:
            current_section["content"].append(line)

    if current_section["content"]:
        sections.append(current_section)

    return sections
