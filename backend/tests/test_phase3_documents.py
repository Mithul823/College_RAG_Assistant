import os
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.security import create_access_token, hash_password
from app.db.base import Base
from app.main import app
from app.models.chunk import DocumentChunk
from app.models.document import Document, DocumentStatus
from app.models.user import User, UserRole
from app.rag.ingestion.chunker import PageAwareChunker
from app.rag.ingestion.cleaner import TextCleaner
from app.rag.ingestion.loader import PDFExtractionError, PDFLoader, PDFValidationError
from app.services.document_service import DocumentService
from tests.conftest import TestingSessionLocal


def create_sample_pdf_bytes() -> bytes:
    """Generate a minimal valid PDF with extracted text content."""
    stream_content = b"BT /F1 12 Tf 72 712 Td (Section 1: Academic Regulations 2026. All students must maintain satisfactory academic progress.) Tj ET"
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


# --- Unit Tests: PDF Loader & Validator ---

def test_validate_pdf_valid() -> None:
    valid_pdf = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
    PDFLoader.validate_pdf(valid_pdf, content_type="application/pdf", max_size_mb=20)


def test_validate_pdf_invalid_signature_raises() -> None:
    invalid_content = b"NOT_A_PDF_CONTENT"
    with pytest.raises(PDFValidationError) as exc:
        PDFLoader.validate_pdf(invalid_content, content_type="application/pdf", max_size_mb=20)
    assert "Invalid file signature" in str(exc.value)


def test_validate_pdf_invalid_mime_raises() -> None:
    valid_pdf = b"%PDF-1.4 sample content"
    with pytest.raises(PDFValidationError) as exc:
        PDFLoader.validate_pdf(valid_pdf, content_type="image/png", max_size_mb=20)
    assert "Invalid content type" in str(exc.value)


def test_validate_pdf_oversized_raises() -> None:
    oversized_pdf = b"%PDF-1.4 " + (b"x" * (2 * 1024 * 1024))
    with pytest.raises(PDFValidationError) as exc:
        PDFLoader.validate_pdf(oversized_pdf, content_type="application/pdf", max_size_mb=1)
    assert "exceeds limit" in str(exc.value)


def test_extract_pages_on_sample_pdf() -> None:
    pdf_bytes = create_sample_pdf_bytes()
    pages = PDFLoader.extract_pages(pdf_bytes)
    assert len(pages) == 1
    assert pages[0]["page_number"] == 1
    assert "Section 1: Academic Regulations" in pages[0]["text"]


# --- Unit Tests: Text Cleaner ---

def test_text_cleaner_normalizes_whitespace_and_newlines() -> None:
    raw_text = "Line 1   with   spaces\r\n\r\n\r\n\r\nLine 2\t\ttabbed\u00a0here\n\n\nLine 3"
    cleaned = TextCleaner.clean_text(raw_text)
    assert "Line 1 with spaces" in cleaned
    assert "Line 2 tabbed here" in cleaned
    assert "\n\n\n" not in cleaned
    assert "\r" not in cleaned


def test_text_cleaner_preserves_regulations_dates_and_numbers() -> None:
    raw_text = "Regulation CS-101: Students must maintain 75% attendance by 2026-09-01. Fee is $250.50."
    cleaned = TextCleaner.clean_text(raw_text)
    assert cleaned == "Regulation CS-101: Students must maintain 75% attendance by 2026-09-01. Fee is $250.50."


# --- Unit Tests: Page-Aware Chunker ---

def test_chunker_preserves_page_numbers_and_metadata() -> None:
    chunker = PageAwareChunker(chunk_size=100, chunk_overlap=10)
    doc_id = uuid4()
    pages = [
        {"page_number": 1, "text": "Section 1: Academic Policies\n\nStudents must complete all prerequisite courses before enrolling in advanced electives."},
        {"page_number": 2, "text": "Section 2: Examination Rules\n\nAll final examinations are held during the scheduled finals week in December."},
    ]

    chunks = chunker.chunk_document(
        pages=pages,
        document_id=doc_id,
        document_name="Handbook.pdf",
        department="Computer Science",
        academic_year="2026",
        semester="Fall",
    )

    assert len(chunks) == 2
    assert chunks[0].page_number == 1
    assert chunks[0].section == "Section 1: Academic Policies"
    assert chunks[0].metadata["department"] == "Computer Science"
    assert chunks[0].metadata["academic_year"] == "2026"
    assert chunks[0].metadata["semester"] == "Fall"
    assert chunks[1].page_number == 2
    assert chunks[1].section == "Section 2: Examination Rules"


# --- Integration Tests: Document API & Ingestion Pipeline ---

def create_user_token(role: UserRole) -> tuple[User, str]:
    with TestingSessionLocal() as database:
        user = User(
            name=f"{role.value.capitalize()} User",
            email=f"{role.value}_{uuid4()}@example.com",
            password_hash=hash_password("password123"),
            role=role,
            is_active=True,
        )
        database.add(user)
        database.commit()
        database.refresh(user)
        token = create_access_token(user_id=user.id, role=user.role)
        return user, token


def test_admin_upload_document_success() -> None:
    admin, token = create_user_token(UserRole.ADMIN)
    pdf_bytes = create_sample_pdf_bytes()

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/documents",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("regulations.pdf", pdf_bytes, "application/pdf")},
            data={
                "title": "Academic Regulations 2026",
                "document_type": "handbook",
                "department": "Engineering",
                "academic_year": "2026",
                "semester": "Fall",
                "version": "1.0",
                "description": "General academic regulations handbook",
            },
        )

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Academic Regulations 2026"
    assert data["filename"] == "regulations.pdf"
    assert data["status"] == "completed"
    assert data["department"] == "Engineering"
    assert data["uploaded_by"] == str(admin.id)

    doc_id = UUID(data["id"])
    with TestingSessionLocal() as database:
        doc = database.query(Document).filter(Document.id == doc_id).one()
        assert doc.status == DocumentStatus.COMPLETED
        assert os.path.exists(doc.file_path)
        # Clean up file created by test
        if os.path.exists(doc.file_path):
            os.remove(doc.file_path)


def test_student_cannot_upload_or_delete_documents() -> None:
    student, student_token = create_user_token(UserRole.STUDENT)
    pdf_bytes = create_sample_pdf_bytes()

    with TestClient(app) as client:
        # Upload attempt
        upload_resp = client.post(
            "/api/v1/documents",
            headers={"Authorization": f"Bearer {student_token}"},
            files={"file": ("test.pdf", pdf_bytes, "application/pdf")},
            data={"title": "Unauthorized Document"},
        )
        assert upload_resp.status_code == 403

        # List attempt
        list_resp = client.get(
            "/api/v1/documents",
            headers={"Authorization": f"Bearer {student_token}"},
        )
        assert list_resp.status_code == 403

        # Delete attempt
        del_resp = client.delete(
            f"/api/v1/documents/{uuid4()}",
            headers={"Authorization": f"Bearer {student_token}"},
        )
        assert del_resp.status_code == 403


def test_upload_invalid_file_signature_rejected() -> None:
    admin, token = create_user_token(UserRole.ADMIN)
    fake_pdf = b"THIS IS NOT A VALID PDF FILE"

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/documents",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("fake.pdf", fake_pdf, "application/pdf")},
            data={"title": "Fake Document"},
        )

    assert response.status_code == 400
    assert "Invalid file signature" in response.json()["detail"]


def test_admin_get_and_list_and_delete_document() -> None:
    admin, token = create_user_token(UserRole.ADMIN)
    pdf_bytes = create_sample_pdf_bytes()

    with TestClient(app) as client:
        # Upload
        create_resp = client.post(
            "/api/v1/documents",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("syllabus.pdf", pdf_bytes, "application/pdf")},
            data={"title": "Syllabus 2026"},
        )
        assert create_resp.status_code == 201
        doc_id = create_resp.json()["id"]

        # List
        list_resp = client.get("/api/v1/documents", headers={"Authorization": f"Bearer {token}"})
        assert list_resp.status_code == 200
        assert list_resp.json()["total"] >= 1

        # Get
        get_resp = client.get(f"/api/v1/documents/{doc_id}", headers={"Authorization": f"Bearer {token}"})
        assert get_resp.status_code == 200
        assert get_resp.json()["id"] == doc_id
        assert "chunks" in get_resp.json()

        # Delete
        del_resp = client.delete(f"/api/v1/documents/{doc_id}", headers={"Authorization": f"Bearer {token}"})
        assert del_resp.status_code == 200
        assert del_resp.json()["status"] == "deleted"

        # Verify not found after deletion
        get_again = client.get(f"/api/v1/documents/{doc_id}", headers={"Authorization": f"Bearer {token}"})
        assert get_again.status_code == 404
