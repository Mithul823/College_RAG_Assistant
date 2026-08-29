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
    """Ultra-lightweight local embedding provider used ONLY for pytest unit testing."""

    def __init__(self, model_name: str | None = None) -> None:
        self.model_name = model_name or "BAAI/bge-small-en-v1.5"
        self._model = None

    @property
    def model(self) -> Any:
        if self._model is None:
            logger.info("loading_fastembed_onnx_model_for_test", extra={"model_name": self.model_name})
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
    """Zero-RAM Remote API Embedding provider using Google Gemini API."""

    def __init__(self, api_key: str | None = None) -> None:
        settings = get_settings()
        self.api_key = api_key or settings.active_api_key
        self.model = "models/gemini-embedding-001"

    def _embed_batch(self, batch_texts: list[str]) -> list[list[float]]:
        if not batch_texts:
            return []
        if not self.api_key or self.api_key == "CHANGE_ME":
            raise RuntimeError("GEMINI_API_KEY is not configured on Render. Please set GEMINI_API_KEY in Render Environment Variables.")

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

        logger.info("connecting_to_gemini_api", extra={"url": url, "batch_count": len(batch_texts)})

        max_retries = 3
        last_error = None

        for attempt in range(max_retries):
            try:
                with httpx.Client(timeout=20.0) as client:
                    res = client.post(url, params=params, json=payload)
                    if res.status_code == 200:
                        data = res.json()
                        embeddings = [e["values"] for e in data.get("embeddings", [])]
                        if len(embeddings) == len(batch_texts):
                            return embeddings
                    elif res.status_code == 429:
                        time.sleep(1.5 * (attempt + 1))
                        continue
                    last_error = f"HTTP {res.status_code}: {res.text[:150]}"
            except Exception as exc:
                last_error = sanitize_credentials(str(exc))

        raise RuntimeError(f"Remote Gemini Embedding API request failed ({last_error}). Please verify your GEMINI_API_KEY on Render.")

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


class HuggingFaceEmbeddingProvider(EmbeddingProvider):
    """Zero-RAM Remote API Embedding provider using Hugging Face Serverless Router & Inference API."""

    def __init__(self, token: str | None = None, model_name: str | None = None) -> None:
        settings = get_settings()
        self.token = token or settings.active_hf_token
        self.model_name = model_name or "sentence-transformers/all-MiniLM-L6-v2"

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if not self.token or self.token == "CHANGE_ME":
            raise RuntimeError("HF_TOKEN is not configured on Render. Please set HF_TOKEN in Render Environment Variables.")

        headers = {"Authorization": f"Bearer {self.token}"}
        batch_size = 16
        all_embeddings: list[list[float]] = []

        endpoints = [
            ("https://router.huggingface.co/hf-inference/v1/embeddings", {"model": self.model_name}),
            (f"https://api-inference.huggingface.co/models/{self.model_name}", None),
        ]

        last_error = None
        for i in range(0, len(texts), batch_size):
            chunk_batch = texts[i : i + batch_size]
            batch_success = False

            for url, extra_payload in endpoints:
                try:
                    payload = {"inputs": chunk_batch} if extra_payload is None else {"model": self.model_name, "input": chunk_batch}
                    logger.info("connecting_to_hf_api", extra={"url": url, "batch_size": len(chunk_batch)})
                    with httpx.Client(timeout=20.0) as client:
                        res = client.post(url, headers=headers, json=payload)
                        if res.status_code == 200:
                            data = res.json()
                            if isinstance(data, list):
                                all_embeddings.extend(data)
                                batch_success = True
                                break
                            elif isinstance(data, dict) and "data" in data:
                                embeddings = [item["embedding"] for item in data["data"]]
                                all_embeddings.extend(embeddings)
                                batch_success = True
                                break
                        last_error = f"HTTP {res.status_code}: {res.text[:150]}"
                except Exception as exc:
                    last_error = sanitize_credentials(str(exc))

            if not batch_success:
                settings = get_settings()
                if settings.active_api_key:
                    logger.warning("hf_inference_api_failed_falling_back_to_gemini", extra={"error": last_error})
                    return GeminiEmbeddingProvider(api_key=settings.active_api_key).embed_documents(texts)
                raise RuntimeError(f"HuggingFace Inference API request failed: {last_error}")

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
    """Return configured embedding provider (FastEmbed ONLY for pytest, Remote APIs for 0 MB RAM overhead on Render)."""
    settings = get_settings()
    if os.getenv("PYTEST_CURRENT_TEST") or settings.app_env == "testing":
        return FastEmbedEmbeddingProvider()

    key = settings.active_api_key
    if key:
        return GeminiEmbeddingProvider(api_key=key)

    hf_token = settings.active_hf_token
    if hf_token:
        return HuggingFaceEmbeddingProvider(token=hf_token)

    return GeminiEmbeddingProvider()
