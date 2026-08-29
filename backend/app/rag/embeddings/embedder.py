from abc import ABC, abstractmethod
from functools import lru_cache
import logging
from typing import Any

import httpx

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


class GeminiEmbeddingProvider(EmbeddingProvider):
    """Zero-RAM Remote API Embedding provider using Google Gemini API (models/gemini-embedding-001)."""

    def __init__(self, api_key: str | None = None) -> None:
        settings = get_settings()
        self.api_key = api_key or settings.llm_api_key
        self.model = "models/gemini-embedding-001"

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if not self.api_key or self.api_key == "CHANGE_ME":
            raise RuntimeError("GEMINI_API_KEY / LLM_API_KEY is not configured for remote embeddings.")

        url = f"https://generativelanguage.googleapis.com/v1beta/{self.model}:batchEmbedContents?key={self.api_key}"
        payload = {
            "requests": [
                {
                    "model": self.model,
                    "content": {"parts": [{"text": t}]}
                }
                for t in texts
            ]
        }

        with httpx.Client(timeout=30.0) as client:
            res = client.post(url, json=payload)
            res.raise_for_status()
            data = res.json()
            embeddings = [e["values"] for e in data.get("embeddings", [])]
            if len(embeddings) == len(texts):
                return embeddings
            raise RuntimeError(f"Unexpected embedding count returned: expected {len(texts)}, got {len(embeddings)}")

    def embed_query(self, text: str) -> list[float]:
        if not text:
            return []
        results = self.embed_documents([text])
        return results[0] if results else []


class FastEmbedEmbeddingProvider(EmbeddingProvider):
    """Ultra-lightweight local embedding provider using FastEmbed ONNX runtime."""

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
    """Legacy SentenceTransformer provider alias."""

    def __init__(self, model_name: str | None = None) -> None:
        self._provider = GeminiEmbeddingProvider()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._provider.embed_documents(texts)

    def embed_query(self, text: str) -> list[float]:
        return self._provider.embed_query(text)


@lru_cache
def get_embedding_provider() -> EmbeddingProvider:
    """Return configured embedding provider (defaults to Remote Gemini API for 0 MB RAM overhead on Render)."""
    settings = get_settings()
    if settings.llm_api_key and settings.llm_api_key != "CHANGE_ME":
        return GeminiEmbeddingProvider()
    return FastEmbedEmbeddingProvider()
