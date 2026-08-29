from dataclasses import dataclass
import logging
import re
from typing import Any
from uuid import UUID

from app.core.config import get_settings
from app.rag.embeddings.embedder import EmbeddingProvider, get_embedding_provider
from app.rag.vectorstore.chroma import ChromaVectorStore, get_vector_store

logger = logging.getLogger(__name__)


@dataclass
class RetrievedChunk:
    chunk_id: str
    document_id: str
    document_name: str
    page_number: int
    section: str | None
    department: str | None
    academic_year: str | None
    semester: str | None
    text: str
    relevance_score: float
    distance: float


class RAGRetriever:
    """Retrieves relevant document chunks using Hybrid Retrieval (Dense Vectors + Keyword Matching)."""

    def __init__(
        self,
        embedding_provider: EmbeddingProvider | None = None,
        vector_store: ChromaVectorStore | None = None,
    ) -> None:
        self.embedding_provider = embedding_provider or get_embedding_provider()
        self.vector_store = vector_store or get_vector_store()
        self.settings = get_settings()

    def _resolve_min_score(self, min_score: float | None = None) -> float:
        if min_score is not None:
            return min_score
        try:
            raw_score = self.settings.min_relevance_score
            if raw_score and raw_score != "CHANGE_ME":
                return float(raw_score)
        except (ValueError, TypeError):
            pass
        return 0.10
    @staticmethod
    def _compute_keyword_score(query: str, text: str) -> float:
        """Compute term frequency and phrase match bonus for exact keyword retrieval."""
        if not query or not text:
            return 0.0

        q_clean = query.lower()
        t_clean = text.lower()

        # Check exact phrase match (high confidence)
        if len(q_clean) > 3 and q_clean in t_clean:
            return 1.0

        stopwords = {
            "what", "when", "where", "which", "who", "whom", "whose", "why", "how",
            "is", "are", "was", "were", "the", "for", "and", "tell", "about", "can",
            "you", "give", "please", "does", "have", "with", "from", "show", "in", "to", "of", "a", "an"
        }
        words = [
            re.sub(r"[^\w]", "", w)
            for w in q_clean.split()
            if len(re.sub(r"[^\w]", "", w)) > 1
        ]
        core_terms = [w for w in words if w not in stopwords]
        if not core_terms:
            core_terms = words

        if not core_terms:
            return 0.0

        matches = sum(1 for term in core_terms if term in t_clean)
        return min(1.0, matches / len(core_terms))

    def retrieve(
        self,
        query: str,
        top_k: int | None = None,
        min_relevance_score: float | None = None,
        where: dict[str, Any] | None = None,
    ) -> list[RetrievedChunk]:
        """Retrieve top-K chunks using hybrid dense semantic and sparse keyword scoring."""
        if not query or not query.strip():
            return []

        effective_top_k = top_k or self.settings.top_k or 5
        effective_min_score = self._resolve_min_score(min_relevance_score)

        # 1. Embed query
        try:
            query_embedding = self.embedding_provider.embed_query(query.strip())
        except Exception as exc:
            logger.warning("retrieval_embedding_failed", extra={"error": str(exc)})
            query_embedding = []

        if not query_embedding:
            return []

        # 2. Vector search in ChromaDB (retrieve candidate pool for hybrid reranking)
        candidate_k = max(effective_top_k * 2, 10)
        raw_results = self.vector_store.query_similar(
            query_embedding=query_embedding,
            top_k=candidate_k,
            where=where,
        )

        # 3. Hybrid fusion scoring
        scored_candidates: list[tuple[float, dict[str, Any]]] = []
        for result in raw_results:
            vector_score = result.get("score", 0.0)
            chunk_text = result.get("text", "")
            keyword_score = self._compute_keyword_score(query, chunk_text)

            # Weighted hybrid score (70% semantic embedding + 30% exact keyword match)
            hybrid_score = (0.70 * vector_score) + (0.30 * keyword_score)
            # Boost if strong keyword match
            if keyword_score >= 0.5:
                hybrid_score = max(hybrid_score, keyword_score * 0.85)

            scored_candidates.append((hybrid_score, result))

        # Sort by hybrid score descending
        scored_candidates.sort(key=lambda x: x[0], reverse=True)

        # 4. Filter by relevance threshold and map to structured dataclass
        retrieved: list[RetrievedChunk] = []
        for hybrid_score, result in scored_candidates:
            if hybrid_score < effective_min_score:
                continue

            metadata = result.get("metadata") or {}
            retrieved.append(
                RetrievedChunk(
                    chunk_id=result.get("chunk_id", ""),
                    document_id=str(metadata.get("document_id", "")),
                    document_name=str(metadata.get("document_name", "Unknown Document")),
                    page_number=int(metadata.get("page_number", 1)) if metadata.get("page_number") else 1,
                    section=metadata.get("section") or None,
                    department=metadata.get("department") or None,
                    academic_year=metadata.get("academic_year") or None,
                    semester=metadata.get("semester") or None,
                    text=result.get("text", ""),
                    relevance_score=round(hybrid_score, 4),
                    distance=result.get("distance", 0.0),
                )
            )
            if len(retrieved) >= effective_top_k:
                break

        logger.info(
            "retrieval_completed",
            extra={
                "query": query[:50],
                "candidates_retrieved": len(raw_results),
                "passed_threshold": len(retrieved),
                "threshold": effective_min_score,
            },
        )
        return retrieved


def get_retriever() -> RAGRetriever:
    """Return an instance of RAGRetriever."""
    return RAGRetriever()
