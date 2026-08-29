from abc import ABC, abstractmethod
from functools import lru_cache
import logging
from typing import Any

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class EmbeddingProvider(ABC):
    """Abstract interface for embedding providers."""

    @abstractmethod
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Generate vector embeddings for a list of document texts."""
        pass

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        """Generate a vector embedding for a single query text."""
        pass


class FastEmbedEmbeddingProvider(EmbeddingProvider):
    """Ultra-lightweight embedding provider using FastEmbed ONNX runtime (<50MB RAM footprint)."""

    def __init__(self, model_name: str | None = None) -> None:
        self.model_name = model_name or "BAAI/bge-small-en-v1.5"
        self._model = None

    @property
    def model(self) -> Any:
        if self._model is None:
            logger.info("loading_fastembed_onnx_model", extra={"model_name": self.model_name})
            from fastembed import TextEmbedding
            self._model = TextEmbedding(model_name=self.model_name)
        return self._model

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        embeddings = list(self.model.embed(texts))
        return [e.tolist() for e in embeddings]

    def embed_query(self, text: str) -> list[float]:
        if not text:
            return []
        embeddings = list(self.model.embed([text]))
        return embeddings[0].tolist()


class SentenceTransformerEmbeddingProvider(EmbeddingProvider):
    """Fallback embedding provider using SentenceTransformers."""

    def __init__(self, model_name: str | None = None) -> None:
        settings = get_settings()
        self.model_name = model_name or settings.embedding_model
        self._model = None

    @property
    def model(self) -> Any:
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        embeddings = self.model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
        return embeddings.tolist()

    def embed_query(self, text: str) -> list[float]:
        if not text:
            return []
        embedding = self.model.encode(text, convert_to_numpy=True, normalize_embeddings=True)
        return embedding.tolist()


@lru_cache
def get_embedding_provider() -> EmbeddingProvider:
    """Return a singleton instance of FastEmbed ONNX embedding provider for low RAM footprint."""
    try:
        return FastEmbedEmbeddingProvider()
    except Exception as e:
        logger.warning("fastembed_fallback_to_sentence_transformers", extra={"error": str(e)})
        return SentenceTransformerEmbeddingProvider()
