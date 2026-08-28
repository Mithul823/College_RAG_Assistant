from io import BytesIO
from uuid import uuid4

from fastapi.testclient import TestClient
from pypdf import PageObject, PdfWriter
import pytest

from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.document import Document, DocumentStatus
from app.models.user import User, UserRole
from tests.conftest import TestingSessionLocal


def create_sample_pdf(text: str) -> bytes:
    stream_content = f"BT /F1 12 Tf 72 712 Td ({text}) Tj ET".encode("ascii", errors="replace")
    stream_len = len(stream_content)
    pdf = (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
        b"4 0 obj\n<< /Length " + str(stream_len).encode("ascii") + b" >>\nstream\n"
        + stream_content + b"\nendstream\nendobj\n"
        b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
        b"xref\n0 6\n"
        b"0000000000 65535 f \n"
        b"0000000010 00000 n \n"
        b"0000000060 00000 n \n"
        b"0000000117 00000 n \n"
        b"0000000234 00000 n \n"
        b"0000000350 00000 n \n"
        b"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n450\n%%EOF\n"
    )
    return pdf


def test_upload_document_with_slashes_and_special_chars_in_filename() -> None:
    db = TestingSessionLocal()
    admin = User(
        name="Admin Test",
        email=f"admin_{uuid4()}@example.com",
        password_hash=hash_password("adminpass"),
        role=UserRole.ADMIN,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    token = create_access_token(admin.id, admin.role)
    db.close()

    pdf_data = create_sample_pdf("Curriculum for Data Scientist (Machine Learning / AI) track.")

    with TestClient(app) as client:
        # Upload with filename containing slashes, parentheses, and spaces
        files = {"file": ("Data Scientist (Machine Learning / AI).pdf", pdf_data, "application/pdf")}
        data = {
            "title": "Data Scientist (Machine Learning / AI)",
            "department": "Computer Science / AI",
            "academic_year": "2025/2026",
            "description": "Specialization track in ML/AI & Data Science.",
        }
        res = client.post(
            "/api/v1/documents",
            headers={"Authorization": f"Bearer {token}"},
            files=files,
            data=data,
        )
        assert res.status_code == 201, f"Expected 201 Created, got {res.status_code}: {res.text}"
        doc = res.json()
        assert doc["status"] == "completed"
        assert "Data Scientist" in doc["title"]

