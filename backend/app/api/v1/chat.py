from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.chat import ChatMessageResponse, ChatRequest, ChatResponse
from app.services.conversation_service import ConversationService

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


@router.post(
    "",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit a query to the College RAG Assistant",
    description="Processes a user question through the evidence-grounded RAG pipeline, stores conversation history, and returns the grounded answer with source citations.",
)
async def chat(
    payload: ChatRequest,
    database: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ChatResponse:
    conversation, message, sources = await ConversationService.process_chat(
        database=database,
        user=current_user,
        message_text=payload.message,
        conversation_id=payload.conversation_id,
    )

    message_response = ChatMessageResponse(
        id=message.id,
        role=message.role.value,
        content=message.content,
        answer_mode=message.answer_mode,
        sources=sources,
        created_at=message.created_at,
    )

    return ChatResponse(
        conversation_id=conversation.id,
        message=message_response,
    )

