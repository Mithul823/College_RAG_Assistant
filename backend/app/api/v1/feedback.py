from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.feedback import MessageFeedback
from app.models.message import Message
from app.models.user import User, UserRole
from app.schemas.feedback import (
    FeedbackAnalyticsResponse,
    FeedbackCreateRequest,
    FeedbackResponse,
)

router = APIRouter(tags=["feedback"])


@router.post(
    "/api/v1/chat/messages/{message_id}/feedback",
    response_model=FeedbackResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit feedback for an assistant message",
    description="Submit thumbs up (1) or thumbs down (-1) feedback with an optional comment on an assistant answer.",
)
def submit_message_feedback(
    message_id: UUID,
    payload: FeedbackCreateRequest,
    database: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FeedbackResponse:
    # Verify message exists
    message = database.scalar(select(Message).where(Message.id == message_id))
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Message with ID '{message_id}' not found",
        )

    # Upsert feedback
    feedback = database.scalar(
        select(MessageFeedback).where(
            MessageFeedback.message_id == message_id,
            MessageFeedback.user_id == current_user.id,
        )
    )

    if feedback:
        feedback.rating = payload.rating
        feedback.comment = payload.comment
    else:
        feedback = MessageFeedback(
            message_id=message_id,
            user_id=current_user.id,
            rating=payload.rating,
            comment=payload.comment,
        )
        database.add(feedback)

    database.commit()
    database.refresh(feedback)
    return FeedbackResponse.model_validate(feedback)


@router.get(
    "/api/v1/chat/messages/{message_id}/feedback",
    response_model=FeedbackResponse | None,
    summary="Get user feedback for a message",
)
def get_message_feedback(
    message_id: UUID,
    database: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FeedbackResponse | None:
    feedback = database.scalar(
        select(MessageFeedback).where(
            MessageFeedback.message_id == message_id,
            MessageFeedback.user_id == current_user.id,
        )
    )
    if not feedback:
        return None
    return FeedbackResponse.model_validate(feedback)


@router.get(
    "/api/v1/admin/analytics/feedback",
    response_model=FeedbackAnalyticsResponse,
    summary="Get student feedback satisfaction analytics",
    description="Calculates total feedback count, positive/negative breakdown, and overall student satisfaction rate. (Admin only)",
)
def get_feedback_analytics(
    database: Session = Depends(get_db),
    current_admin: User = Depends(require_role(UserRole.ADMIN)),
) -> FeedbackAnalyticsResponse:
    total = database.scalar(select(func.count(MessageFeedback.id))) or 0
    positive = (
        database.scalar(select(func.count(MessageFeedback.id)).where(MessageFeedback.rating == 1))
        or 0
    )
    negative = (
        database.scalar(select(func.count(MessageFeedback.id)).where(MessageFeedback.rating == -1))
        or 0
    )

    satisfaction_rate = round((positive / total * 100.0), 1) if total > 0 else 100.0

    return FeedbackAnalyticsResponse(
        total_feedback=total,
        positive_count=positive,
        negative_count=negative,
        satisfaction_rate=satisfaction_rate,
    )

