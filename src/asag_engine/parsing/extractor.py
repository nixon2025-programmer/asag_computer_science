from __future__ import annotations
import os

def extract_text_from_file(path: str) -> str:
    ext = os.path.splitext(path)[1].lower().strip(".")
    if ext == "pdf":
        return _extract_pdf(path)
    if ext == "docx":
        return _extract_docx(path)
    raise ValueError(f"Unsupported file type: .{ext} (supported: pdf, docx)")

def _extract_pdf(path: str) -> str:
    import pdfplumber
    parts = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            t = (page.extract_text() or "").strip()
            if t:
                parts.append(t)
    return "\n\n".join(parts).strip()

def _extract_docx(path: str) -> str:
    from docx import Document
    doc = Document(path)
    parts = []
    for p in doc.paragraphs:
        t = (p.text or "").strip()
        if t:
            parts.append(t)
    return "\n".join(parts).strip()