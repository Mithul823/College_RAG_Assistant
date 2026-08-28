from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.db.session import get_db
from app.models.chunk import DocumentChunk
from app.models.conversation import Conversation
from app.models.document import Document, DocumentStatus
from app.models.message import Message
from app.models.user import User, UserRole
from app.rag.vectorstore.chroma import get_vector_store
from app.schemas.admin import AdminMetricsResponse, StatusBreakdown

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


@router.get(
    "/metrics",
    response_model=AdminMetricsResponse,
    summary="Get administrative and knowledge base metrics",
    description="Returns aggregated metrics regarding uploaded documents, chunks, conversations, messages, and vector database status. (Admin only)",
)
def get_admin_metrics(
    database: Session = Depends(get_db),
    current_admin: User = Depends(require_role(UserRole.ADMIN)),
) -> AdminMetricsResponse:
    total_docs = database.scalar(select(func.count(Document.id))) or 0
    total_chunks = database.scalar(select(func.count(DocumentChunk.id))) or 0
    total_convs = database.scalar(select(func.count(Conversation.id))) or 0
    total_msgs = database.scalar(select(func.count(Message.id))) or 0

    # Status breakdown
    status_counts_raw = database.execute(
        select(Document.status, func.count(Document.id)).group_by(Document.status)
    ).all()

    breakdown = {
        "completed": 0,
        "processing": 0,
        "failed": 0,
        "uploaded": 0,
    }
    for status_val, count in status_counts_raw:
        key = status_val.value if hasattr(status_val, "value") else str(status_val).lower()
        if key in breakdown:
            breakdown[key] = count

    # Vector store count
    total_vectors = 0
    try:
        store = get_vector_store()
        total_vectors = store.collection.count()
    except Exception:
        total_vectors = total_chunks

    return AdminMetricsResponse(
        total_documents=total_docs,
        total_chunks=total_chunks,
        total_conversations=total_convs,
        total_messages=total_msgs,
        total_vectors=total_vectors,
        status_breakdown=StatusBreakdown(**breakdown),
    )

