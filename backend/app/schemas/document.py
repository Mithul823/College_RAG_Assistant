from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.document import DocumentStatus


class DocumentChunkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    chunk_index: int
    document_name: str
    page_number: int
    section: str | None = None
    department: str | None = None
    academic_year: str | None = None
    semester: str | None = None
    text: str
    token_count: int | None = None
    created_at: datetime


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    filename: str
    document_type: str | None = None
    department: str | None = None
    academic_year: str | None = None
    semester: str | None = None
    version: str | None = None
    description: str | None = None
    status: DocumentStatus
    uploaded_by: UUID
    created_at: datetime
    updated_at: datetime


class DocumentDetailResponse(DocumentResponse):
    chunks: list[DocumentChunkResponse] = []


class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]
    total: int

