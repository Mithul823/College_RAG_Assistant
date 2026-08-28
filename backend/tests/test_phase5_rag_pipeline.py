from uuid import uuid4

import pytest

from app.rag.embeddings.embedder import get_embedding_provider
from app.rag.generation.engine import RAGEngine, SourceCitation, get_rag_engine
from app.rag.generation.llm import MockLLMProvider, UNKNOWN_ANSWER_TEXT
from app.rag.generation.prompt import DEFAULT_SYSTEM_PROMPT, PromptBuilder
from app.rag.ingestion.chunker import ProcessedChunk
from app.rag.retrieval.retriever import RAGRetriever, RetrievedChunk, get_retriever
from app.rag.vectorstore.chroma import ChromaVectorStore, get_vector_store


@pytest.fixture
def seeded_vector_store() -> tuple[ChromaVectorStore, uuid4, uuid4]:
    """Helper to populate vector store with test academic chunks."""
    store = get_vector_store()
    doc_id = uuid4()
    chunk_id_1 = uuid4()
    chunk_id_2 = uuid4()

    chunks = [
        ProcessedChunk(
            id=chunk_id_1,
            document_id=doc_id,
            chunk_index=0,
            page_number=5,
            section="Attendance Regulations",
            text="All undergraduate students must maintain a minimum of 75 percent attendance to be eligible for end-semester examinations.",
            token_count=18,
            metadata={
                "document_id": str(doc_id),
                "chunk_id": str(chunk_id_1),
                "chunk_index": 0,
                "document_name": "Academic Regulations 2026.pdf",
                "page_number": 5,
                "section": "Attendance Regulations",
                "department": "Academics",
                "academic_year": "2026",
                "semester": "All",
            },
        ),
        ProcessedChunk(
            id=chunk_id_2,
            document_id=doc_id,
            chunk_index=1,
            page_number=12,
            section="Library Rules",
            text="Books borrowed from the central library must be returned within 14 calendar days to avoid overdue fines.",
            token_count=17,
            metadata={
                "document_id": str(doc_id),
                "chunk_id": str(chunk_id_2),
                "chunk_index": 1,
                "document_name": "Academic Regulations 2026.pdf",
                "page_number": 12,
                "section": "Library Rules",
                "department": "Library",
                "academic_year": "2026",
                "semester": "All",
            },
        ),
    ]

    provider = get_embedding_provider()
    embeddings = provider.embed_documents([c.text for c in chunks])
    store.add_chunks(chunks, embeddings)

    return store, doc_id, chunk_id_1


# --- Unit Tests: Retriever ---

def test_retriever_empty_query_returns_empty() -> None:
    retriever = get_retriever()
    assert retriever.retrieve("") == []
    assert retriever.retrieve("   ") == []


def test_retriever_filters_by_min_relevance_score(seeded_vector_store) -> None:
    _, doc_id, _ = seeded_vector_store
    retriever = get_retriever()

    # Query with low threshold -> retrieves relevant chunks
    results_normal = retriever.retrieve("attendance policy", top_k=2, min_relevance_score=0.1)
    assert len(results_normal) > 0
    assert results_normal[0].section == "Attendance Regulations"
    assert results_normal[0].page_number == 5

    # Query with unreasonably high threshold -> filters out chunks
    results_filtered = retriever.retrieve("attendance policy", top_k=2, min_relevance_score=0.999)
    assert len(results_filtered) == 0


# --- Unit Tests: Prompt Builder ---

def test_prompt_builder_context_formatting() -> None:
    chunks = [
        RetrievedChunk(
            chunk_id="chunk-1",
            document_id="doc-1",
            document_name="Regulations.pdf",
            page_number=18,
            section="Attendance",
            department="General",
            academic_year="2026",
            semester=None,
            text="Minimum 75% attendance required.",
            relevance_score=0.88,
            distance=0.12,
        )
    ]

    formatted = PromptBuilder.format_context(chunks)
    assert "SOURCE 1" in formatted
    assert "Document: Regulations.pdf" in formatted
    assert "Page: 18" in formatted
    assert "Section: Attendance" in formatted
    assert "Minimum 75% attendance required." in formatted


def test_prompt_builder_user_prompt_with_history() -> None:
    chunks = [
        RetrievedChunk(
            chunk_id="chunk-1",
            document_id="doc-1",
            document_name="Regulations.pdf",
            page_number=18,
            section="Attendance",
            department="General",
            academic_year="2026",
            semester=None,
            text="Minimum 75% attendance required.",
            relevance_score=0.88,
            distance=0.12,
        )
    ]
    history = [
        {"role": "user", "content": "Hi, I have a question."},
        {"role": "assistant", "content": "Hello! How can I help you today?"},
    ]

    user_prompt = PromptBuilder.build_user_prompt(
        question="What is the attendance requirement?",
        chunks=chunks,
        conversation_history=history,
    )

    assert "RETRIEVED CONTEXT:" in user_prompt
    assert "CONVERSATION HISTORY:" in user_prompt
    assert "User: Hi, I have a question." in user_prompt
    assert "QUESTION: What is the attendance requirement?" in user_prompt


import asyncio


# --- Unit Tests: LLM Provider ---

def test_mock_llm_provider_behavior() -> None:
    mock_llm = MockLLMProvider()

    # Grounded turn
    grounded_res = asyncio.run(
        mock_llm.generate_response(
            prompt="Sample prompt with context",
            source_chunk_ids=["uuid-1", "uuid-2"],
        )
    )
    assert grounded_res.answer_mode == "grounded"
    assert len(grounded_res.source_chunk_ids) == 2

    # Unknown turn
    unknown_res = asyncio.run(
        mock_llm.generate_response(
            prompt="Sample prompt without context: No relevant context retrieved.",
            source_chunk_ids=[],
        )
    )
    assert unknown_res.answer_mode == "unknown"
    assert unknown_res.answer == UNKNOWN_ANSWER_TEXT


# --- Integration Tests: End-to-End RAG Engine ---

def test_rag_engine_grounded_answer(seeded_vector_store) -> None:
    rag_engine = RAGEngine(llm_provider=MockLLMProvider())

    response = asyncio.run(
        rag_engine.generate_answer(
            question="What is the minimum attendance required for exams?",
            min_relevance_score=0.1,
        )
    )

    assert response.answer_mode == "grounded"
    assert len(response.sources) > 0
    assert response.sources[0].page_number == 5
    assert response.sources[0].document_name == "Academic Regulations 2026.pdf"
    assert response.retrieval_latency > 0
    assert response.response_latency >= response.retrieval_latency


def test_rag_engine_unknown_answer_behavior(seeded_vector_store) -> None:
    rag_engine = RAGEngine(llm_provider=MockLLMProvider())

    # Query for completely unrelated knowledge with strict threshold
    response = asyncio.run(
        rag_engine.generate_answer(
            question="What is the recipe for chocolate cake?",
            min_relevance_score=0.85,
        )
    )

    assert response.answer_mode == "unknown"
    assert response.answer == UNKNOWN_ANSWER_TEXT
    assert response.sources == []
    assert response.source_chunk_ids == []
