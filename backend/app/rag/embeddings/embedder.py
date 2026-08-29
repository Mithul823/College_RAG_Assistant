from abc import ABC, abstractmethod
from functools import lru_cache
import logging
import os
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


class SentenceTransformerEmbeddingProvider(EmbeddingProvider):
    """Embedding provider using Sentence Transformers with lazy-loading and low RAM footprint."""

    def __init__(self, model_name: str | None = None) -> None:
        settings = get_settings()
        self.model_name = model_name or settings.embedding_model
        self._model = None

    @property
    def model(self) -> Any:
        if self._model is None:
            # Enforce single-threaded execution to stay within Render 512MB RAM limits
            os.environ["OMP_NUM_THREADS"] = "1"
            os.environ["MKL_NUM_THREADS"] = "1"
            os.environ["OPENBLAS_NUM_THREADS"] = "1"
            try:
                import torch
                torch.set_num_threads(1)
            except Exception:
                pass

            logger.info("loading_embedding_model", extra={"model_name": self.model_name})
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
    """Return a singleton instance of the configured embedding provider."""
    settings = get_settings()
    return SentenceTransformerEmbeddingProvider(model_name=settings.embedding_model)
