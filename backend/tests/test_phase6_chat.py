from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.chunk import DocumentChunk
from app.models.conversation import Conversation
from app.models.document import Document, DocumentStatus
from app.models.message import Message, MessageRole, MessageSource
from app.models.user import User, UserRole
from app.rag.embeddings.embedder import get_embedding_provider
from app.rag.generation.llm import UNKNOWN_ANSWER_TEXT
from app.rag.ingestion.chunker import ProcessedChunk
from app.rag.vectorstore.chroma import get_vector_store
from tests.conftest import TestingSessionLocal


def create_user_token(role: UserRole, email_prefix: str = "user") -> tuple[User, str]:
    with TestingSessionLocal() as database:
        user = User(
            name=f"{role.value.capitalize()} User",
            email=f"{email_prefix}_{uuid4()}@example.com",
            password_hash=hash_password("password123"),
            role=role,
            is_active=True,
        )
        database.add(user)
        database.commit()
        database.refresh(user)
        token = create_access_token(user_id=user.id, role=user.role)
        return user, token


def seed_document_and_chunks(uploader_id: UUID) -> tuple[Document, list[DocumentChunk]]:
    with TestingSessionLocal() as database:
        doc = Document(
            id=uuid4(),
            title="Academic Handbook 2026",
            filename="Academic_Handbook_2026.pdf",
            document_type="handbook",
            department="Academics",
            academic_year="2026",
            semester="Fall",
            status=DocumentStatus.COMPLETED,
            file_path="/tmp/fake.pdf",
            uploaded_by=uploader_id,
        )
        database.add(doc)
        database.commit()
        database.refresh(doc)

        chunk1 = DocumentChunk(
            id=uuid4(),
            document_id=doc.id,
            chunk_index=0,
            document_name=doc.filename,
            page_number=4,
            section="Attendance",
            department="Academics",
            academic_year="2026",
            semester="Fall",
            text="Undergraduate students must maintain at least 75 percent attendance in every registered course.",
            token_count=16,
        )
        chunk2 = DocumentChunk(
            id=uuid4(),
            document_id=doc.id,
            chunk_index=1,
            document_name=doc.filename,
            page_number=10,
            section="Tuition Fees",
            department="Finance",
            academic_year="2026",
            semester="Fall",
            text="Semester tuition fees must be cleared by August 15th to maintain active student registration status.",
            token_count=17,
        )
        database.add_all([chunk1, chunk2])
        database.commit()
        database.refresh(chunk1)
        database.refresh(chunk2)

        # Also insert vectors into Chroma
        processed_chunks = [
            ProcessedChunk(
                id=chunk1.id,
                document_id=doc.id,
                chunk_index=0,
                page_number=4,
                section="Attendance",
                text=chunk1.text,
                token_count=chunk1.token_count,
                metadata={
                    "document_id": str(doc.id),
                    "chunk_id": str(chunk1.id),
                    "chunk_index": 0,
                    "document_name": doc.filename,
                    "page_number": 4,
                    "section": "Attendance",
                    "department": "Academics",
                    "academic_year": "2026",
                    "semester": "Fall",
                },
            ),
            ProcessedChunk(
                id=chunk2.id,
                document_id=doc.id,
                chunk_index=1,
                page_number=10,
                section="Tuition Fees",
                text=chunk2.text,
                token_count=chunk2.token_count,
                metadata={
                    "document_id": str(doc.id),
                    "chunk_id": str(chunk2.id),
                    "chunk_index": 1,
                    "document_name": doc.filename,
                    "page_number": 10,
                    "section": "Tuition Fees",
                    "department": "Finance",
                    "academic_year": "2026",
                    "semester": "Fall",
                },
            ),
        ]
        provider = get_embedding_provider()
        embeddings = provider.embed_documents([c.text for c in processed_chunks])
        vector_store = get_vector_store()
        vector_store.add_chunks(processed_chunks, embeddings)

        return doc, [chunk1, chunk2]


# --- Integration Tests: Chat API ---

def test_chat_creates_new_conversation_when_id_is_none() -> None:
    student, token = create_user_token(UserRole.STUDENT, "student1")
    doc, chunks = seed_document_and_chunks(student.id)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={"message": "What is the attendance requirement for undergraduates?"},
        )

    assert response.status_code == 200
    data = response.json()
    assert "conversation_id" in data
    assert data["message"]["role"] == "assistant"
    assert data["message"]["answer_mode"] == "grounded"
    assert len(data["message"]["sources"]) > 0
    assert data["message"]["sources"][0]["document_name"] == "Academic_Handbook_2026.pdf"
    assert data["message"]["sources"][0]["page_number"] == 4

    conv_id = UUID(data["conversation_id"])
    with TestingSessionLocal() as database:
        conv = database.query(Conversation).filter(Conversation.id == conv_id).one()
        assert conv.user_id == student.id
        assert len(conv.messages) == 2  # 1 user + 1 assistant
        assert conv.messages[0].role == MessageRole.USER
        assert conv.messages[1].role == MessageRole.ASSISTANT
        assert len(conv.messages[1].sources) > 0


def test_chat_appends_to_existing_conversation() -> None:
    student, token = create_user_token(UserRole.STUDENT, "student2")
    doc, chunks = seed_document_and_chunks(student.id)

    with TestClient(app) as client:
        # Turn 1
        resp1 = client.post(
            "/api/v1/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={"message": "What is the attendance requirement?"},
        )
        assert resp1.status_code == 200
        conv_id = resp1.json()["conversation_id"]

        # Turn 2
        resp2 = client.post(
            "/api/v1/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={"conversation_id": conv_id, "message": "When is the tuition fee deadline?"},
        )
        assert resp2.status_code == 200
        assert resp2.json()["conversation_id"] == conv_id

    with TestingSessionLocal() as database:
        conv = database.query(Conversation).filter(Conversation.id == UUID(conv_id)).one()
        assert len(conv.messages) == 4  # 2 user + 2 assistant


def test_chat_unknown_question_returns_fallback_message() -> None:
    student, token = create_user_token(UserRole.STUDENT, "student3")

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={"message": "What is the secret recipe for Martian pizza?"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["message"]["answer_mode"] == "unknown"
    assert data["message"]["content"] == UNKNOWN_ANSWER_TEXT
    assert data["message"]["sources"] == []


def test_chat_cross_user_isolation_prevented() -> None:
    student1, token1 = create_user_token(UserRole.STUDENT, "alice")
    student2, token2 = create_user_token(UserRole.STUDENT, "bob")

    with TestClient(app) as client:
        # Alice creates a conversation
        resp1 = client.post(
            "/api/v1/chat",
            headers={"Authorization": f"Bearer {token1}"},
            json={"message": "Hello Alice conversation"},
        )
        conv_id = resp1.json()["conversation_id"]

        # Bob attempts to post into Alice's conversation
        resp2 = client.post(
            "/api/v1/chat",
            headers={"Authorization": f"Bearer {token2}"},
            json={"conversation_id": conv_id, "message": "Bob intruding"},
        )
        assert resp2.status_code == 403

        # Bob attempts to get Alice's conversation
        resp3 = client.get(
            f"/api/v1/conversations/{conv_id}",
            headers={"Authorization": f"Bearer {token2}"},
        )
        assert resp3.status_code == 403

        # Bob attempts to delete Alice's conversation
        resp4 = client.delete(
            f"/api/v1/conversations/{conv_id}",
            headers={"Authorization": f"Bearer {token2}"},
        )
        assert resp4.status_code == 403


def test_conversations_listing_detail_and_deletion() -> None:
    student, token = create_user_token(UserRole.STUDENT, "carol")
    doc, chunks = seed_document_and_chunks(student.id)

    with TestClient(app) as client:
        # Create 2 conversations
        c1 = client.post(
            "/api/v1/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={"message": "What is the minimum attendance requirement for undergraduate students?"},
        ).json()["conversation_id"]

        c2 = client.post(
            "/api/v1/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={"message": "When must semester tuition fees be cleared by students?"},
        ).json()["conversation_id"]

        # List conversations
        list_resp = client.get(
            "/api/v1/conversations",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert list_resp.status_code == 200
        data = list_resp.json()
        assert data["total"] == 2
        assert len(data["conversations"]) == 2

        # Get conversation detail
        get_resp = client.get(
            f"/api/v1/conversations/{c1}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert get_resp.status_code == 200
        detail = get_resp.json()
        assert detail["id"] == c1
        assert len(detail["messages"]) == 2
        assert detail["messages"][1]["sources"][0]["page_number"] == 4

        # Delete conversation
        del_resp = client.delete(
            f"/api/v1/conversations/{c1}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert del_resp.status_code == 200
        assert del_resp.json()["status"] == "deleted"

        # Verify 404 after deletion
        get_again = client.get(
            f"/api/v1/conversations/{c1}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert get_again.status_code == 404
