from pydantic import BaseModel, Field


class StatusBreakdown(BaseModel):
    completed: int = 0
    processing: int = 0
    failed: int = 0
    uploaded: int = 0


class AdminMetricsResponse(BaseModel):
    total_documents: int = Field(..., description="Total number of uploaded documents")
    total_chunks: int = Field(..., description="Total number of indexed text chunks")
    total_conversations: int = Field(..., description="Total student conversations")
    total_messages: int = Field(..., description="Total student messages")
    total_vectors: int = Field(..., description="Total vectors stored in ChromaDB")
    status_breakdown: StatusBreakdown = Field(..., description="Document status count breakdown")

