from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class FeedbackCreateRequest(BaseModel):
    rating: int = Field(..., description="1 for thumbs up, -1 for thumbs down", ge=-1, le=1)
    comment: str | None = Field(default=None, max_length=1000, description="Optional textual feedback comment")


class FeedbackResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    message_id: UUID
    user_id: UUID
    rating: int
    comment: str | None
    created_at: datetime


class FeedbackAnalyticsResponse(BaseModel):
    total_feedback: int
    positive_count: int
    negative_count: int
    satisfaction_rate: float  # Percentage 0-100
