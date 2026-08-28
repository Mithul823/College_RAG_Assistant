from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.chat import SourceCitationResponse
from app.schemas.conversation import (
    ConversationDetailResponse,
    ConversationListResponse,
    ConversationResponse,
    MessageDetailResponse,
)
from app.services.conversation_service import ConversationService

router = APIRouter(prefix="/api/v1/conversations", tags=["conversations"])


@router.get(
    "",
    response_model=ConversationListResponse,
    summary="List conversations",
    description="Returns a paginated list of conversations belonging to the authenticated user.",
)
def list_conversations(
    skip: int = 0,
    limit: int = 50,
    database: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ConversationListResponse:
    conversations, total = ConversationService.list_conversations(
        database=database,
        user=current_user,
        skip=skip,
        limit=limit,
    )
    return ConversationListResponse(
        conversations=[ConversationResponse.model_validate(c) for c in conversations],
        total=total,
    )


@router.get(
    "/{conversation_id}",
    response_model=ConversationDetailResponse,
    summary="Get conversation details and messages",
    description="Returns the full conversation message history and source citations.",
)
def get_conversation(
    conversation_id: UUID,
    database: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ConversationDetailResponse:
    conversation = ConversationService.get_conversation(
        database=database,
        user=current_user,
        conversation_id=conversation_id,
    )

    messages_data: list[MessageDetailResponse] = []
    for msg in conversation.messages:
        sources_data: list[SourceCitationResponse] = []
        for src in msg.sources:
            sources_data.append(
                SourceCitationResponse(
                    document_id=src.document_id,
                    document_name=src.document.filename if src.document else "Unknown Document",
                    page_number=src.chunk.page_number if src.chunk else 1,
                    section=src.chunk.section if src.chunk else None,
                    relevance_score=src.relevance_score,
                )
            )

        messages_data.append(
            MessageDetailResponse(
                id=msg.id,
                conversation_id=msg.conversation_id,
                role=msg.role.value,
                content=msg.content,
                answer_mode=msg.answer_mode,
                sources=sources_data,
                created_at=msg.created_at,
            )
        )

    return ConversationDetailResponse(
        id=conversation.id,
        user_id=conversation.user_id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        messages=messages_data,
    )


@router.delete(
    "/{conversation_id}",
    summary="Delete a conversation",
    description="Deletes a conversation and all its associated messages.",
)
def delete_conversation(
    conversation_id: UUID,
    database: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict[str, str]:
    ConversationService.delete_conversation(
        database=database,
        user=current_user,
        conversation_id=conversation_id,
    )
    return {"status": "deleted", "conversation_id": str(conversation_id)}

