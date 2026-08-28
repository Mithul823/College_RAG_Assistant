from dataclasses import dataclass, field
import logging
import time
from typing import Any

from app.rag.generation.llm import LLMProvider, UNKNOWN_ANSWER_TEXT, get_llm_provider
from app.rag.generation.prompt import DEFAULT_SYSTEM_PROMPT, PromptBuilder
from app.rag.retrieval.retriever import RAGRetriever, RetrievedChunk, get_retriever

logger = logging.getLogger(__name__)


@dataclass
class SourceCitation:
    chunk_id: str
    document_id: str
    document_name: str
    page_number: int
    section: str | None
    relevance_score: float


@dataclass
class RAGResponse:
    answer: str
    sources: list[SourceCitation] = field(default_factory=list)
    source_chunk_ids: list[str] = field(default_factory=list)
    answer_mode: str = "grounded"  # "grounded", "unknown", "error"
    retrieval_latency: float = 0.0
    response_latency: float = 0.0


class RAGEngine:
    """End-to-end RAG pipeline coordinating retrieval, prompt formatting, and grounded generation."""

    def __init__(
        self,
        retriever: RAGRetriever | None = None,
        llm_provider: LLMProvider | None = None,
    ) -> None:
        self.retriever = retriever or get_retriever()
        self.llm_provider = llm_provider or get_llm_provider()

    async def generate_answer(
        self,
        question: str,
        conversation_history: list[dict[str, str]] | None = None,
        top_k: int | None = None,
        min_relevance_score: float | None = None,
        where: dict[str, Any] | None = None,
    ) -> RAGResponse:
        """Execute the evidence-grounded RAG query workflow."""
        start_time = time.perf_counter()

        # 1. Retrieval
        retrieval_start = time.perf_counter()
        retrieved_chunks = self.retriever.retrieve(
            query=question,
            top_k=top_k,
            min_relevance_score=min_relevance_score,
            where=where,
        )
        retrieval_latency = time.perf_counter() - retrieval_start

        # 2. Unknown check: if no evidence satisfies the relevance threshold
        if not retrieved_chunks:
            total_latency = time.perf_counter() - start_time
            logger.info(
                "rag_unknown_fallback_triggered",
                extra={"question": question, "latency": total_latency},
            )
            return RAGResponse(
                answer=UNKNOWN_ANSWER_TEXT,
                sources=[],
                source_chunk_ids=[],
                answer_mode="unknown",
                retrieval_latency=retrieval_latency,
                response_latency=total_latency,
            )

        # 3. Prompt Construction
        chunk_ids = [chunk.chunk_id for chunk in retrieved_chunks]
        user_prompt = PromptBuilder.build_user_prompt(
            question=question,
            chunks=retrieved_chunks,
            conversation_history=conversation_history,
        )

        # 4. LLM Grounded Generation
        generation_start = time.perf_counter()
        llm_result = await self.llm_provider.generate_response(
            prompt=user_prompt,
            system_prompt=DEFAULT_SYSTEM_PROMPT,
            source_chunk_ids=chunk_ids,
        )
        total_latency = time.perf_counter() - start_time

        # 5. Source Mapping
        sources: list[SourceCitation] = [
            SourceCitation(
                chunk_id=chunk.chunk_id,
                document_id=chunk.document_id,
                document_name=chunk.document_name,
                page_number=chunk.page_number,
                section=chunk.section,
                relevance_score=chunk.relevance_score,
            )
            for chunk in retrieved_chunks
        ]

        return RAGResponse(
            answer=llm_result.answer,
            sources=sources,
            source_chunk_ids=chunk_ids,
            answer_mode=llm_result.answer_mode,
            retrieval_latency=retrieval_latency,
            response_latency=total_latency,
        )


def get_rag_engine() -> RAGEngine:
    """Return an instance of the RAGEngine."""
    return RAGEngine()

