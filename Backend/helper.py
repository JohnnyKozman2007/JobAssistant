import io
import pypdf
import docx


class Helper:

    @staticmethod
    def parse_resume_text(file_name: str, file_bytes: bytes) -> str:
        if file_name.endswith(".pdf"):
            return Helper._parse_pdf(file_bytes)
        elif file_name.endswith(".docx"):
            return Helper._parse_docx(file_bytes)
        raise ValueError(f"Unsupported file type: {file_name}")

    @staticmethod
    def _parse_pdf(file_bytes: bytes) -> str:
        reader = pypdf.PdfReader(io.BytesIO(file_bytes))
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    @staticmethod
    def _parse_docx(file_bytes: bytes) -> str:
        doc = docx.Document(io.BytesIO(file_bytes))
        return "\n".join(p.text for p in doc.paragraphs)
