from abc import ABC, abstractmethod
from functools import lru_cache
import logging
import os
import re
import time
from typing import Any

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def sanitize_credentials(text: str) -> str:
    """Scrub sensitive API keys, tokens, passwords, and query parameters from error strings."""
    if not text:
        return ""
    text = re.sub(r"(?:key|token|api_key|password|secret)=[^&\s\"\']+", "[REDACTED]", text, flags=re.IGNORECASE)
    text = re.sub(r"Bearer\s+[A-Za-z0-9\-\._~\+\/]+=*", "Bearer [REDACTED]", text, flags=re.IGNORECASE)
    return text


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


class GeminiEmbeddingProvider(EmbeddingProvider):
    """Zero-RAM Remote API Embedding provider using Google Gemini API (Strict 0 MB RAM overhead for Render)."""

    def __init__(self, api_key: str | None = None) -> None:
        settings = get_settings()
        self.api_key = api_key or settings.gemini_api_key or settings.llm_api_key
        self.model = "models/gemini-embedding-001"

    def _embed_batch(self, batch_texts: list[str]) -> list[list[float]]:
        if not batch_texts:
            return []
        if not self.api_key or self.api_key == "CHANGE_ME":
            raise RuntimeError("GEMINI_API_KEY is not configured on Render. Please add GEMINI_API_KEY to Render Environment Variables.")

        url = f"https://generativelanguage.googleapis.com/v1beta/{self.model}:batchEmbedContents"
        params = {"key": self.api_key}
        payload = {
            "requests": [
                {
                    "model": self.model,
                    "content": {"parts": [{"text": t}]}
                }
                for t in batch_texts
            ]
        }

        max_retries = 3
        last_error = None

        for attempt in range(max_retries):
            try:
                with httpx.Client(timeout=30.0) as client:
                    res = client.post(url, params=params, json=payload)
                    if res.status_code == 200:
                        data = res.json()
                        embeddings = [e["values"] for e in data.get("embeddings", [])]
                        if len(embeddings) == len(batch_texts):
                            return embeddings
                    elif res.status_code == 429:
                        time.sleep(1.0 * (attempt + 1))
                        continue
                    last_error = f"HTTP {res.status_code}"
            except Exception as exc:
                last_error = sanitize_credentials(str(exc))

        raise RuntimeError(f"Remote Gemini Embedding API request failed ({last_error}). Please check GEMINI_API_KEY on Render.")

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        batch_size = 16
        all_embeddings: list[list[float]] = []

        for i in range(0, len(texts), batch_size):
            chunk_batch = texts[i : i + batch_size]
            batch_embeddings = self._embed_batch(chunk_batch)
            all_embeddings.extend(batch_embeddings)

        return all_embeddings

    def embed_query(self, text: str) -> list[float]:
        if not text:
            return []
        results = self.embed_documents([text])
        return results[0] if results else []


class SentenceTransformerEmbeddingProvider(EmbeddingProvider):
    """Legacy SentenceTransformer provider alias."""

    def __init__(self, model_name: str | None = None) -> None:
        self._provider = get_embedding_provider()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._provider.embed_documents(texts)

    def embed_query(self, text: str) -> list[float]:
        return self._provider.embed_query(text)


@lru_cache
def get_embedding_provider() -> EmbeddingProvider:
    """Return configured embedding provider (FastEmbed for tests, Gemini API for 0 MB RAM overhead on Render)."""
    settings = get_settings()
    if os.getenv("PYTEST_CURRENT_TEST") or settings.app_env == "testing":
        return FastEmbedEmbeddingProvider()

    key = settings.gemini_api_key or settings.llm_api_key
    if key and key != "CHANGE_ME":
        return GeminiEmbeddingProvider()
    return GeminiEmbeddingProvider()
