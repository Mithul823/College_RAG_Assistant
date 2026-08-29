from functools import lru_cache
import logging
import os
from pathlib import Path
from typing import Any
from uuid import UUID

# Disable ChromaDB anonymized telemetry to prevent blocked DLL gRPC imports
os.environ["ANONYMIZED_TELEMETRY"] = "False"

import chromadb
from chromadb.api.models.Collection import Collection

from app.core.config import get_settings
from app.rag.ingestion.chunker import ProcessedChunk

logger = logging.getLogger(__name__)


from chromadb import EmbeddingFunction, Documents, Embeddings


class NullEmbeddingFunction(EmbeddingFunction[Documents]):
    def name(self) -> str:
        return "null_embedding_function"

    def __call__(self, input: Documents) -> Embeddings:
        return [[] for _ in input]


null_ef = NullEmbeddingFunction()


class ChromaVectorStore:
    """ChromaDB persistent vector store implementation."""

    def __init__(
        self,
        persist_directory: str | None = None,
        collection_name: str | None = None,
    ) -> None:
        settings = get_settings()
        self.persist_directory = persist_directory or settings.chroma_persist_directory
        self.collection_name = collection_name or settings.chroma_collection_name

        # Ensure directory exists
        Path(self.persist_directory).mkdir(parents=True, exist_ok=True)

        logger.info(
            "initializing_chroma_client",
            extra={
                "persist_directory": self.persist_directory,
                "collection_name": self.collection_name,
            },
        )
        self.client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=chromadb.config.Settings(anonymized_telemetry=False),
        )
        try:
            self.collection: Collection = self.client.get_or_create_collection(
                name=self.collection_name,
                embedding_function=null_ef,
                metadata={"hnsw:space": "cosine"},
            )
        except Exception:
            try:
                self.collection: Collection = self.client.get_collection(
                    name=self.collection_name,
                )
            except Exception:
                self.client.delete_collection(name=self.collection_name)
                self.collection: Collection = self.client.get_or_create_collection(
                    name=self.collection_name,
                    embedding_function=null_ef,
                    metadata={"hnsw:space": "cosine"},
                )

    def reset(self) -> None:
        """Clear collection records safely."""
        try:
            self.client.delete_collection(name=self.collection_name)
        except Exception:
            pass
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=null_ef,
            metadata={"hnsw:space": "cosine"},
        )

    @staticmethod
    def _sanitize_metadata(metadata: dict[str, Any]) -> dict[str, str | int | float | bool]:
        """Convert metadata values to types accepted by ChromaDB (str, int, float, bool)."""
        sanitized: dict[str, str | int | float | bool] = {}
        for key, value in metadata.items():
            if value is None:
                sanitized[key] = ""
            elif isinstance(value, (str, int, float, bool)):
                sanitized[key] = value
            else:
                sanitized[key] = str(value)
        return sanitized

    def add_chunks(
        self, chunks: list[ProcessedChunk], embeddings: list[list[float]]
    ) -> None:
        """Insert or update chunks and their embeddings in the vector collection."""
        if not chunks:
            return

        ids = [str(chunk.id) for chunk in chunks]
        documents = [chunk.text for chunk in chunks]
        metadatas = [self._sanitize_metadata(chunk.metadata) for chunk in chunks]

        self.collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )
        logger.info(
            "vectors_inserted",
            extra={"collection": self.collection_name, "count": len(chunks)},
        )

    def query_similar(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        where: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Retrieve top-K most similar chunks for a given query embedding."""
        query_args: dict[str, Any] = {
            "query_embeddings": [query_embedding],
            "n_results": top_k,
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            query_args["where"] = where

        results = self.collection.query(**query_args)

        retrieved: list[dict[str, Any]] = []
        ids = results.get("ids", [[]])[0]
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        for i in range(len(ids)):
            distance = distances[i] if distances is not None and i < len(distances) else 0.0
            dist_val = float(distance)
            if dist_val > 1.0:
                similarity = max(0.0, min(1.0, 1.0 - (dist_val / 2.0)))
            else:
                similarity = max(0.0, min(1.0, 1.0 - dist_val))

            retrieved.append(
                {
                    "chunk_id": ids[i],
                    "text": documents[i] if documents else "",
                    "metadata": metadatas[i] if metadatas else {},
                    "distance": dist_val,
                    "score": round(similarity, 4),
                }
            )

        return retrieved

    def delete_by_document_id(self, document_id: UUID) -> None:
        """Delete all vectors associated with a document ID."""
        doc_id_str = str(document_id)
        try:
            self.collection.delete(where={"document_id": doc_id_str})
            logger.info(
                "vectors_deleted",
                extra={"collection": self.collection_name, "document_id": doc_id_str},
            )
        except Exception as exc:
            logger.error(
                "vector_deletion_failed",
                extra={"document_id": doc_id_str, "error": str(exc)},
            )
            raise RuntimeError(
                f"Failed to delete vector embeddings for document '{doc_id_str}': {exc}"
            ) from exc

    def count(self) -> int:
        """Return total vector count in the collection."""
        return self.collection.count()


@lru_cache
def get_vector_store() -> ChromaVectorStore:
    """Return a singleton instance of the ChromaDB vector store."""
    return ChromaVectorStore()

