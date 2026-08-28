from io import BytesIO
from uuid import uuid4

from fastapi.testclient import TestClient
from pypdf import PageObject, PdfWriter
import pytest

from app.core.security import create_access_token, hash_password
from app.db.session import get_db
from app.main import app
from app.models.chunk import DocumentChunk
from app.models.conversation import Conversation
from app.models.document import Document, DocumentStatus
from app.models.message import Message, MessageRole
from app.models.user import User, UserRole
from app.rag.vectorstore.chroma import get_vector_store
from tests.conftest import TestingSessionLocal


def create_user_token(role: UserRole, prefix: str = "test") -> tuple[User, str]:
    db = TestingSessionLocal()
    user = User(
        name=f"{prefix} User",
        email=f"{prefix}_{uuid4()}@example.com",
        password_hash=hash_password("password123"),
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(user.id, user.role)
    db.close()
    return user, token


def create_minimal_pdf_bytes(title: str, body_text: str) -> bytes:
    writer = PdfWriter()
    page = PageObject.create_blank_page(width=612, height=792)
    writer.add_page(page)
    stream = BytesIO()
    writer.write(stream)
    return stream.getvalue()


def test_admin_metrics_requires_admin_role() -> None:
    student, student_token = create_user_token(UserRole.STUDENT, "student_user")
    admin, admin_token = create_user_token(UserRole.ADMIN, "admin_user")

    with TestClient(app) as client:
        # Student request should be rejected with 403 Forbidden
        student_resp = client.get(
            "/api/v1/admin/metrics",
            headers={"Authorization": f"Bearer {student_token}"},
        )
        assert student_resp.status_code == 403

        # Admin request should succeed with 200 OK
        admin_resp = client.get(
            "/api/v1/admin/metrics",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert admin_resp.status_code == 200
        data = admin_resp.json()
        assert "total_documents" in data
        assert "total_chunks" in data
        assert "total_conversations" in data
        assert "total_messages" in data
        assert "total_vectors" in data
        assert "status_breakdown" in data


def test_admin_metrics_accuracy() -> None:
    admin, admin_token = create_user_token(UserRole.ADMIN, "admin_metrics")
    student, student_token = create_user_token(UserRole.STUDENT, "student_metrics")

    db = TestingSessionLocal()

    # Seed 2 documents
    doc1 = Document(
        title="Doc One",
        filename="doc1.pdf",
        file_path="data/uploads/doc1.pdf",
        status=DocumentStatus.COMPLETED,
        uploaded_by=admin.id,
    )
    doc2 = Document(
        title="Doc Two",
        filename="doc2.pdf",
        file_path="data/uploads/doc2.pdf",
        status=DocumentStatus.PROCESSING,
        uploaded_by=admin.id,
    )
    db.add_all([doc1, doc2])
    db.commit()
    db.refresh(doc1)

    # Seed 2 chunks
    chunk1 = DocumentChunk(
        document_id=doc1.id,
        chunk_index=0,
        document_name=doc1.filename,
        text="Chunk 1 content",
        page_number=1,
    )
    chunk2 = DocumentChunk(
        document_id=doc1.id,
        chunk_index=1,
        document_name=doc1.filename,
        text="Chunk 2 content",
        page_number=2,
    )
    db.add_all([chunk1, chunk2])

    # Seed conversation and message
    conv = Conversation(user_id=student.id, title="Test Conversation")
    db.add(conv)
    db.commit()
    db.refresh(conv)

    msg = Message(
        conversation_id=conv.id,
        role=MessageRole.USER,
        content="Test question",
    )
    db.add(msg)
    db.commit()
    db.close()

    with TestClient(app) as client:
        resp = client.get(
            "/api/v1/admin/metrics",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_documents"] == 2
        assert data["total_chunks"] == 2
        assert data["total_conversations"] == 1
        assert data["total_messages"] == 1
        assert data["status_breakdown"]["completed"] == 1
        assert data["status_breakdown"]["processing"] == 1


def test_admin_get_document_chunks_and_deletion() -> None:
    admin, admin_token = create_user_token(UserRole.ADMIN, "admin_mgmt")
    db = TestingSessionLocal()

    doc = Document(
        title="Exam Guidelines 2026",
        filename="exam_guide.pdf",
        file_path="data/uploads/test_exam_guide.pdf",
        status=DocumentStatus.COMPLETED,
        uploaded_by=admin.id,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    chunk = DocumentChunk(
        document_id=doc.id,
        chunk_index=0,
        document_name=doc.filename,
        text="Final examinations require 75% attendance.",
        page_number=1,
    )
    db.add(chunk)
    db.commit()
    db.close()

    with TestClient(app) as client:
        # Get document detail with chunks
        detail_resp = client.get(
            f"/api/v1/documents/{doc.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert detail_resp.status_code == 200
        detail_data = detail_resp.json()
        assert detail_data["id"] == str(doc.id)
        assert len(detail_data["chunks"]) == 1
        assert "75% attendance" in detail_data["chunks"][0]["text"]

        # Delete document
        del_resp = client.delete(
            f"/api/v1/documents/{doc.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert del_resp.status_code == 200
        assert del_resp.json()["status"] == "deleted"

        # Verify not found afterwards
        not_found_resp = client.get(
            f"/api/v1/documents/{doc.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert not_found_resp.status_code == 404
