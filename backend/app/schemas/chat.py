from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    conversation_id: UUID | None = None
    message: str = Field(..., min_length=1, max_length=4000, description="User question or prompt")


class SourceCitationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    document_id: UUID
    chunk_id: UUID | None = None
    document_name: str
    page_number: int
    section: str | None = None
    relevance_score: float
    chunk_text: str | None = None


class ChatMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    role: str
    content: str
    answer_mode: str | None = None
    sources: list[SourceCitationResponse] = []
    latency_ms: float | None = None
    user_feedback: int | None = None  # 1 for positive, -1 for negative, None if unrated
    created_at: datetime


class ChatResponse(BaseModel):
    conversation_id: UUID
    message: ChatMessageResponse
