import os
from pathlib import Path
import tempfile
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.chunk import DocumentChunk
from app.models.document import Document, DocumentStatus
from app.models.user import User, UserRole
from app.rag.embeddings.embedder import (
    EmbeddingProvider,
    SentenceTransformerEmbeddingProvider,
    get_embedding_provider,
)
from app.rag.ingestion.chunker import ProcessedChunk
from app.rag.vectorstore.chroma import ChromaVectorStore, get_vector_store
from tests.conftest import TestingSessionLocal


def create_sample_pdf_bytes() -> bytes:
    """Generate a minimal valid PDF with extracted text content."""
    stream_content = b"BT /F1 12 Tf 72 712 Td (Section 1: Computer Science Department Grading Policy 2026. Minimum GPA required is 3.0.) Tj ET"
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


# --- Embedding Provider Tests ---

def test_embedding_provider_interface() -> None:
    provider = get_embedding_provider()
    assert isinstance(provider, EmbeddingProvider)


def test_sentence_transformer_embed_query_and_documents() -> None:
    provider = get_embedding_provider()
    
    # Query embedding
    query = "What is the minimum attendance requirement?"
    query_emb = provider.embed_query(query)
    assert isinstance(query_emb, list)
    assert len(query_emb) == 384  # all-MiniLM-L6-v2 dimension
    assert all(isinstance(val, float) for val in query_emb)

    # Document embeddings
    docs = [
        "Students must maintain 75 percent attendance.",
        "Computer science degree requires 120 credit units.",
    ]
    doc_embs = provider.embed_documents(docs)
    assert len(doc_embs) == 2
    assert len(doc_embs[0]) == 384
    assert len(doc_embs[1]) == 384


def test_embedding_provider_singleton() -> None:
    provider1 = get_embedding_provider()
    provider2 = get_embedding_provider()
    assert provider1 is provider2


# --- Vector Store Tests ---

def test_chroma_vector_store_lifecycle() -> None:
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
        store = ChromaVectorStore(
            persist_directory=temp_dir,
            collection_name=f"test_col_{uuid4().hex[:8]}",
        )
        doc_id = uuid4()
        chunk_id_1 = uuid4()
        chunk_id_2 = uuid4()

        chunks = [
            ProcessedChunk(
                id=chunk_id_1,
                document_id=doc_id,
                chunk_index=0,
                page_number=1,
                section="Grading",
                text="Students must maintain a 3.0 GPA in core courses.",
                token_count=12,
                metadata={
                    "document_id": str(doc_id),
                    "chunk_id": str(chunk_id_1),
                    "chunk_index": 0,
                    "document_name": "Handbook.pdf",
                    "page_number": 1,
                    "section": "Grading",
                    "department": "CS",
                    "academic_year": "2026",
                    "semester": "Fall",
                },
            ),
            ProcessedChunk(
                id=chunk_id_2,
                document_id=doc_id,
                chunk_index=1,
                page_number=2,
                section="Tuition",
                text="Tuition fee must be paid before semester registration.",
                token_count=10,
                metadata={
                    "document_id": str(doc_id),
                    "chunk_id": str(chunk_id_2),
                    "chunk_index": 1,
                    "document_name": "Handbook.pdf",
                    "page_number": 2,
                    "section": "Tuition",
                    "department": "Finance",
                    "academic_year": "2026",
                    "semester": "Fall",
                },
            ),
        ]

        provider = get_embedding_provider()
        embeddings = provider.embed_documents([c.text for c in chunks])

        # Add vectors
        store.add_chunks(chunks, embeddings)
        assert store.count() == 2

        # Query similar
        query_emb = provider.embed_query("What GPA is required for graduation?")
        results = store.query_similar(query_embedding=query_emb, top_k=2)

        assert len(results) == 2
        assert "score" in results[0]
        assert results[0]["score"] > 0
        # The grading chunk should be top result for GPA query
        assert results[0]["chunk_id"] == str(chunk_id_1)

        # Query with metadata filtering
        filtered_results = store.query_similar(
            query_embedding=query_emb,
            top_k=2,
            where={"department": "Finance"},
        )
        assert len(filtered_results) == 1
        assert filtered_results[0]["chunk_id"] == str(chunk_id_2)

        # Delete by document ID
        store.delete_by_document_id(doc_id)
        assert store.count() == 0


# --- End-to-End Ingestion & Vector Synchronization Test ---

def test_document_ingestion_and_vector_sync() -> None:
    admin, token = create_user_token(UserRole.ADMIN)
    pdf_bytes = create_sample_pdf_bytes()

    vector_store = get_vector_store()
    initial_vector_count = vector_store.count()

    with TestClient(app) as client:
        # 1. Upload document -> automatically extracted, chunked, embedded, and stored in Chroma
        upload_resp = client.post(
            "/api/v1/documents",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("grading_policy.pdf", pdf_bytes, "application/pdf")},
            data={
                "title": "Grading Policy 2026",
                "document_type": "policy",
                "department": "Computer Science",
                "academic_year": "2026",
                "semester": "Fall",
            },
        )
        assert upload_resp.status_code == 201
        doc_data = upload_resp.json()
        doc_id = UUID(doc_data["id"])

        # Vector store count should increase
        assert vector_store.count() > initial_vector_count

        # Query vector store for similarity
        provider = get_embedding_provider()
        query_emb = provider.embed_query("minimum GPA policy for computer science")
        results = vector_store.query_similar(
            query_embedding=query_emb,
            top_k=3,
            where={"document_id": str(doc_id)},
        )
        assert any(r["metadata"].get("document_id") == str(doc_id) for r in results)

        # 2. Delete document -> deletes DB record, file from disk, and vectors from Chroma
        del_resp = client.delete(
            f"/api/v1/documents/{doc_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert del_resp.status_code == 200

        # Vector store should no longer contain vectors for this document
        post_del_results = vector_store.query_similar(
            query_embedding=query_emb,
            top_k=5,
            where={"document_id": str(doc_id)},
        )
        assert len(post_del_results) == 0
