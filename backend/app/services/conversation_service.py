from datetime import datetime
import logging
import time
from typing import Any
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.chunk import DocumentChunk
from app.models.conversation import Conversation
from app.models.document import Document
from app.models.message import Message, MessageRole, MessageSource
from app.models.user import User, UserRole
from app.rag.generation.engine import RAGEngine, get_rag_engine
from app.schemas.chat import SourceCitationResponse

logger = logging.getLogger(__name__)


class ConversationService:
    @staticmethod
    def get_or_create_conversation(
        database: Session,
        user: User,
        conversation_id: UUID | None = None,
        initial_title: str | None = None,
    ) -> Conversation:
        if conversation_id is not None:
            conversation = database.scalar(
                select(Conversation).where(Conversation.id == conversation_id)
            )
            if not conversation:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Conversation with ID '{conversation_id}' not found",
                )
            if conversation.user_id != user.id and user.role != UserRole.ADMIN:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to access this conversation",
                )
            return conversation

        # Generate concise conversation title from initial message text
        title = "New Conversation"
        if initial_title:
            cleaned = initial_title.strip().split("\n")[0]
            title = (cleaned[:57] + "...") if len(cleaned) > 60 else cleaned

        new_conv = Conversation(
            id=uuid4(),
            user_id=user.id,
            title=title,
        )
        database.add(new_conv)
        database.commit()
        database.refresh(new_conv)
        return new_conv

    @staticmethod
    def get_recent_history(
        database: Session,
        conversation_id: UUID,
        max_turns: int = 10,
    ) -> list[dict[str, str]]:
        messages = database.scalars(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(max_turns)
        ).all()

        # Reverse to chronological order
        history: list[dict[str, str]] = []
        for msg in reversed(messages):
            history.append({"role": msg.role.value, "content": msg.content})
        return history

    @classmethod
    async def process_chat(
        cls,
        database: Session,
        user: User,
        message_text: str,
        conversation_id: UUID | None = None,
        rag_engine: RAGEngine | None = None,
    ) -> tuple[Conversation, Message, list[SourceCitationResponse]]:
        engine = rag_engine or get_rag_engine()

        # 1. Get or create conversation
        conversation = cls.get_or_create_conversation(
            database=database,
            user=user,
            conversation_id=conversation_id,
            initial_title=message_text,
        )

        # 2. Fetch recent conversation context (last 6-10 messages)
        history = cls.get_recent_history(database, conversation.id, max_turns=8)

        # 3. Store user message in database
        user_message = Message(
            id=uuid4(),
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content=message_text.strip(),
            answer_mode=None,
        )
        database.add(user_message)
        database.commit()

        # 4. Generate RAG answer with latency telemetry
        start_time = time.perf_counter()
        rag_response = await engine.generate_answer(
            question=message_text.strip(),
            conversation_history=history,
        )
        elapsed_latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

        # 5. Store assistant message in database
        assistant_message = Message(
            id=uuid4(),
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content=rag_response.answer,
            answer_mode=rag_response.answer_mode,
        )
        database.add(assistant_message)
        database.commit()
        database.refresh(assistant_message)

        # 6. Store message sources in database
        source_responses: list[SourceCitationResponse] = []
        for rank, citation in enumerate(rag_response.sources, start=1):
            try:
                doc_uuid = UUID(str(citation.document_id))
                chunk_uuid = UUID(str(citation.chunk_id))
            except (ValueError, TypeError):
                continue

            # Ensure referenced document and chunk exist in relational DB
            doc = database.scalar(select(Document).where(Document.id == doc_uuid))
            chunk = database.scalar(select(DocumentChunk).where(DocumentChunk.id == chunk_uuid))
            if not doc or not chunk:
                continue

            msg_source = MessageSource(
                id=uuid4(),
                message_id=assistant_message.id,
                document_id=doc_uuid,
                chunk_id=chunk_uuid,
                relevance_score=citation.relevance_score,
                rank=rank,
            )
            database.add(msg_source)

            source_responses.append(
                SourceCitationResponse(
                    document_id=doc_uuid,
                    chunk_id=chunk_uuid,
                    document_name=citation.document_name,
                    page_number=citation.page_number,
                    section=citation.section,
                    relevance_score=citation.relevance_score,
                    chunk_text=chunk.text,
                )
            )

        # Touch conversation updated_at
        conversation.updated_at = datetime.now()
        database.commit()
        database.refresh(conversation)

        # Attach latency to message object for API response
        setattr(assistant_message, "latency_ms", elapsed_latency_ms)

        return conversation, assistant_message, source_responses

        return conversation, assistant_message, source_responses

    @staticmethod
    def list_conversations(
        database: Session,
        user: User,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[Conversation], int]:
        query = select(Conversation)
        if user.role != UserRole.ADMIN:
            query = query.where(Conversation.user_id == user.id)

        total = database.scalar(select(func.count()).select_from(query.subquery())) or 0
        conversations = database.scalars(
            query.order_by(Conversation.updated_at.desc()).offset(skip).limit(limit)
        ).all()
        return list(conversations), total

    @staticmethod
    def get_conversation(
        database: Session,
        user: User,
        conversation_id: UUID,
    ) -> Conversation:
        conversation = database.scalar(
            select(Conversation)
            .where(Conversation.id == conversation_id)
            .options(
                selectinload(Conversation.messages)
                .selectinload(Message.sources)
                .selectinload(MessageSource.document),
                selectinload(Conversation.messages)
                .selectinload(Message.sources)
                .selectinload(MessageSource.chunk),
            )
        )
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation with ID '{conversation_id}' not found",
            )
        if conversation.user_id != user.id and user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this conversation",
            )
        return conversation

    @staticmethod
    def delete_conversation(
        database: Session,
        user: User,
        conversation_id: UUID,
    ) -> bool:
        conversation = database.scalar(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation with ID '{conversation_id}' not found",
            )
        if conversation.user_id != user.id and user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this conversation",
            )

        database.delete(conversation)
        database.commit()
        return True

