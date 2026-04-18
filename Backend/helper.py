from __future__ import annotations

import io

from docx import Document
from pypdf import PdfReader


class Helper:
    @staticmethod
    def parse_resume_text(file_bytes: bytes, mimetype: str | None = None) -> str:
        if not file_bytes:
            raise ValueError("Resume file is empty.")

        kind = (mimetype or "").lower()

        if "pdf" in kind:
            text = Helper._parse_pdf(file_bytes)
        elif "word" in kind or "officedocument" in kind or "docx" in kind:
            text = Helper._parse_docx(file_bytes)
        elif "text/plain" in kind or kind.endswith(".txt"):
            text = file_bytes.decode("utf-8", errors="ignore")
        else:
            # Try common formats as a fallback when content type is missing.
            text = Helper._parse_pdf(file_bytes)
            if not text.strip():
                text = Helper._parse_docx(file_bytes)
            if not text.strip():
                text = file_bytes.decode("utf-8", errors="ignore")

        cleaned = text.strip()
        if not cleaned:
            raise ValueError("Resume content could not be extracted.")
        return cleaned

    @staticmethod
    def _parse_pdf(file_bytes: bytes) -> str:
        reader = PdfReader(io.BytesIO(file_bytes))
        parts: list[str] = []
        for page in reader.pages:
            parts.append((page.extract_text() or "").strip())
        return "\n".join(part for part in parts if part)

    @staticmethod
    def _parse_docx(file_bytes: bytes) -> str:
        doc = Document(io.BytesIO(file_bytes))
        return "\n".join(paragraph.text.strip() for paragraph in doc.paragraphs if paragraph.text.strip())
