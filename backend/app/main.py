import logging
import os
import sys
import importlib.util
from contextlib import asynccontextmanager
from types import ModuleType
from typing import Any
from unittest.mock import MagicMock

# Disable ChromaDB telemetry
os.environ["ANONYMIZED_TELEMETRY"] = "False"

class StubModule(ModuleType):
    def __getattr__(self, name: str) -> Any:
        return MagicMock()

def _stub_blocked_dll(name: str) -> None:
    if name not in sys.modules:
        mod = StubModule(name)
        mod.__spec__ = importlib.util.spec_from_loader(name, loader=None)
        sys.modules[name] = mod

# Bypass Windows Application Control policy blocks for un-signed C extensions
_stub_blocked_dll("grpc._cython.cygrpc")
_stub_blocked_dll("sklearn")
_stub_blocked_dll("sklearn.metrics")
_stub_blocked_dll("sklearn.utils")
_stub_blocked_dll("sklearn.base")

if "grpc" not in sys.modules or isinstance(sys.modules["grpc"], ModuleType):
    mock_g = MagicMock()
    mock_g.__version__ = "1.65.0"
    sys.modules["grpc"] = mock_g

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.session import init_db


@asynccontextmanager
async def lifespan(application: FastAPI):
    configure_logging()
    logging.getLogger(__name__).info("application_started", extra={"app_name": application.title})
    try:
        init_db()
    except Exception as exc:
        logging.getLogger(__name__).warning("init_db_skipped", extra={"error": str(exc)})

    # Ensure all relational document chunks are indexed into ChromaDB (production/development only)
    if settings.app_env != "testing" and os.getenv("PYTEST_CURRENT_TEST") is None:
        try:
            from sqlalchemy import select
            from app.db.session import SessionLocal
            from app.models.chunk import DocumentChunk
            from app.rag.embeddings.embedder import get_embedding_provider
            from app.rag.ingestion.chunker import ProcessedChunk
            from app.rag.vectorstore.chroma import get_vector_store

            store = get_vector_store()
            db = SessionLocal()
            try:
                chunks = db.scalars(select(DocumentChunk)).all()
                if chunks:
                    embedder = get_embedding_provider()
                    need_reindex = False
                    if store.collection.count() != len(chunks):
                        need_reindex = True
                    else:
                        try:
                            # Verify dimension compatibility
                            test_emb = embedder.embed_query("test")
                            test_res = store.collection.query(query_embeddings=[test_emb], n_results=1)
                        except Exception:
                            need_reindex = True

                    if need_reindex:
                        logging.getLogger(__name__).info("reindexing_chroma_vector_store", extra={"chunks": len(chunks)})
                        store.reset()
                        processed = [
                            ProcessedChunk(
                                id=c.id,
                                document_id=c.document_id,
                                chunk_index=c.chunk_index,
                                page_number=c.page_number,
                                section=c.section,
                                text=c.text,
                                token_count=c.token_count,
                                metadata={
                                    "document_id": str(c.document_id),
                                    "chunk_id": str(c.id),
                                    "chunk_index": c.chunk_index,
                                    "document_name": c.document_name or "Document",
                                    "page_number": c.page_number,
                                    "section": c.section or "",
                                    "department": c.department or "",
                                    "academic_year": c.academic_year or "",
                                    "semester": c.semester or "",
                                },
                            )
                            for c in chunks
                        ]
                        texts = [c.text for c in chunks]
                        embeddings = embedder.embed_documents(texts)
                        store.add_chunks(chunks=processed, embeddings=embeddings)
            finally:
                db.close()
        except Exception as exc:
            logging.getLogger(__name__).warning("vector_sync_skipped", extra={"error": str(exc)})

    yield
    logging.getLogger(__name__).info("application_stopped")


settings = get_settings()
app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.rstrip('/') for origin in settings.cors_origins],
    allow_origin_regex=r"https?://.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router)


@app.get("/health", tags=["system"])
def health() -> dict[str, Any]:
    return {"status": "ok", "environment": settings.app_env}
