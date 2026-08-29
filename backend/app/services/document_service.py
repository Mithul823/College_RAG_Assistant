import logging
import os
from pathlib import Path
import re
from typing import Any
from uuid import UUID, uuid4

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.models.chunk import DocumentChunk
from app.models.document import Document, DocumentStatus
from app.rag.embeddings.embedder import get_embedding_provider
from app.rag.ingestion.chunker import PageAwareChunker
from app.rag.ingestion.cleaner import TextCleaner
from app.rag.ingestion.loader import PDFExtractionError, PDFLoader, PDFValidationError
from app.rag.vectorstore.chroma import get_vector_store

logger = logging.getLogger(__name__)


class DocumentService:
    @staticmethod
    def _ensure_upload_directory() -> Path:
        settings = get_settings()
        upload_path = Path(settings.upload_dir).resolve()
        upload_path.mkdir(parents=True, exist_ok=True)
        return upload_path

    @classmethod
    async def create_and_process_document(
        cls,
        database: Session,
        file: UploadFile,
        title: str,
        uploaded_by: UUID,
        document_type: str | None = None,
        department: str | None = None,
        academic_year: str | None = None,
        semester: str | None = None,
        version: str | None = None,
        description: str | None = None,
    ) -> Document:
        settings = get_settings()
        upload_dir = cls._ensure_upload_directory()

        # Read file bytes
        content = await file.read()
        filename = file.filename or "uploaded_document.pdf"

        # Validate PDF
        try:
            PDFLoader.validate_pdf(
                content=content,
                content_type=file.content_type,
                max_size_mb=settings.max_file_size_mb,
            )
        except PDFValidationError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc

        # Sanitize filename for safe disk path on Windows/Linux
        clean_name = re.sub(r'[\\/*?:"<>|\x00]', "_", filename).strip() or "document.pdf"
        if not clean_name.lower().endswith(".pdf"):
            clean_name += ".pdf"

        # Save to disk
        doc_id = uuid4()
        safe_filename = f"{doc_id}_{clean_name}"
        saved_file_path = upload_dir / safe_filename

        try:
            with open(saved_file_path, "wb") as buffer:
                buffer.write(content)
        except Exception as exc:
            logger.error("file_save_failed", extra={"error": str(exc), "filename": filename})
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save uploaded file to storage",
            ) from exc

        # Sanitize string inputs against NUL bytes
        clean_title = title.replace("\x00", "").strip() or clean_name
        clean_desc = description.replace("\x00", "").strip() if description else None
        clean_dept = department.replace("\x00", "").strip() if department else None

        # Create database record
        document = Document(
            id=doc_id,
            title=clean_title,
            filename=clean_name,
            document_type=document_type,
            department=clean_dept,
            academic_year=academic_year,
            semester=semester,
            version=version,
            description=clean_desc,
            status=DocumentStatus.PROCESSING,
            file_path=str(saved_file_path),
            uploaded_by=uploaded_by,
        )
        database.add(document)
        database.commit()
        database.refresh(document)

        # Ingestion pipeline: Extract -> Clean -> Chunk -> Embed -> Insert Vectors -> Save DB Chunks
        try:
            pages = PDFLoader.extract_pages(content)
            cleaned_pages = [
                {"page_number": p["page_number"], "text": TextCleaner.clean_text(p["text"])}
                for p in pages
            ]

            chunker = PageAwareChunker(chunk_size=500, chunk_overlap=50)
            chunks = chunker.chunk_document(
                pages=cleaned_pages,
                document_id=doc_id,
                document_name=filename,
                department=department,
                academic_year=academic_year,
                semester=semester,
            )

            # Fallback if no text extracted (e.g. scanned image-only PDF)
            if not chunks:
                fallback_text = (
                    f"Document: {title}\n"
                    f"Filename: {filename}\n"
                    f"Department: {department or 'General'}\n"
                    f"Academic Year: {academic_year or 'N/A'}\n"
                    f"Description: {description or 'Official institutional document'}"
                )
                fallback_id = uuid4()
                chunks = [
                    ProcessedChunk(
                        id=fallback_id,
                        document_id=doc_id,
                        chunk_index=0,
                        page_number=1,
                        section="Document Overview",
                        text=fallback_text,
                        token_count=len(fallback_text.split()),
                        metadata={
                            "document_id": str(doc_id),
                            "chunk_id": str(fallback_id),
                            "chunk_index": 0,
                            "document_name": filename,
                            "page_number": 1,
                            "section": "Document Overview",
                            "department": department or "",
                            "academic_year": academic_year or "",
                            "semester": semester or "",
                        },
                    )
                ]

            # Generate embeddings and store vectors in ChromaDB
            embedding_provider = get_embedding_provider()
            chunk_texts = [chunk.text for chunk in chunks]
            embeddings = embedding_provider.embed_documents(chunk_texts)
            vector_store = get_vector_store()
            vector_store.add_chunks(chunks=chunks, embeddings=embeddings)

            # Persist chunk records in relational database
            for chunk in chunks:
                chunk_record = DocumentChunk(
                    id=chunk.id,
                    document_id=chunk.document_id,
                    chunk_index=chunk.chunk_index,
                    document_name=filename,
                    page_number=chunk.page_number,
                    section=chunk.section,
                    department=department,
                    academic_year=academic_year,
                    semester=semester,
                    text=chunk.text,
                    token_count=chunk.token_count,
                )
                database.add(chunk_record)

            document.status = DocumentStatus.COMPLETED
            database.commit()
            database.refresh(document)
            logger.info(
                "document_ingestion_completed",
                extra={"document_id": str(doc_id), "chunks_count": len(chunks)},
            )
            return document

        except (PDFExtractionError, Exception) as exc:
            logger.error(
                "document_ingestion_failed",
                extra={"document_id": str(doc_id), "error": str(exc)},
            )
            try:
                database.rollback()
                failed_doc = database.scalar(select(Document).where(Document.id == doc_id))
                if failed_doc:
                    failed_doc.status = DocumentStatus.FAILED
                    database.commit()
            except Exception:
                pass
            from app.rag.embeddings.embedder import sanitize_credentials
            clean_error = sanitize_credentials(str(exc))
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Document processing failed: {clean_error}",
            ) from exc

    @staticmethod
    def get_document(database: Session, document_id: UUID) -> Document | None:
        return database.scalar(
            select(Document)
            .where(Document.id == document_id)
            .options(selectinload(Document.chunks))
        )

    @staticmethod
    def list_documents(
        database: Session, skip: int = 0, limit: int = 100
    ) -> tuple[list[Document], int]:
        total = database.scalar(select(func.count(Document.id))) or 0
        documents = database.scalars(
            select(Document)
            .order_by(Document.created_at.desc())
            .offset(skip)
            .limit(limit)
        ).all()
        return list(documents), total

    @staticmethod
    def delete_document(database: Session, document_id: UUID) -> bool:
        document = database.scalar(select(Document).where(Document.id == document_id))
        if not document:
            return False

        # Delete vectors from vector store
        try:
            vector_store = get_vector_store()
            vector_store.delete_by_document_id(document_id)
        except Exception as exc:
            logger.error(
                "vector_deletion_error_on_document_delete",
                extra={"document_id": str(document_id), "error": str(exc)},
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete document vector embeddings: {exc}",
            ) from exc

        # Remove file from disk if present
        if document.file_path and os.path.exists(document.file_path):
            try:
                os.remove(document.file_path)
            except OSError as exc:
                logger.warning(
                    "file_deletion_failed",
                    extra={"file_path": document.file_path, "error": str(exc)},
                )

        database.delete(document)
        database.commit()
        logger.info("document_deleted", extra={"document_id": str(document_id)})
        return True
