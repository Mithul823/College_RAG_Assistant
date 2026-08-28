from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.document import DocumentDetailResponse, DocumentListResponse, DocumentResponse
from app.services.document_service import DocumentService

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])


@router.post(
    "",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and ingest a college PDF document",
    description="Uploads a PDF document, validates content signature, extracts text page-by-page, cleans, chunks, and creates database records. (Admin only)",
)
async def upload_document(
    file: Annotated[UploadFile, File(description="PDF document to upload")],
    title: Annotated[str, Form(description="Document title")],
    document_type: Annotated[str | None, Form(description="Document category/type")] = None,
    department: Annotated[str | None, Form(description="Academic department")] = None,
    academic_year: Annotated[str | None, Form(description="Academic year (e.g. 2026)")] = None,
    semester: Annotated[str | None, Form(description="Semester")] = None,
    version: Annotated[str | None, Form(description="Document version (e.g. 1.0)")] = None,
    description: Annotated[str | None, Form(description="Document description")] = None,
    database: Session = Depends(get_db),
    current_admin: User = Depends(require_role(UserRole.ADMIN)),
) -> DocumentResponse:
    document = await DocumentService.create_and_process_document(
        database=database,
        file=file,
        title=title,
        uploaded_by=current_admin.id,
        document_type=document_type,
        department=department,
        academic_year=academic_year,
        semester=semester,
        version=version,
        description=description,
    )
    return DocumentResponse.model_validate(document)


@router.get(
    "",
    response_model=DocumentListResponse,
    summary="List all uploaded documents",
    description="Returns a paginated list of all uploaded college documents. (Admin only)",
)
def list_documents(
    skip: int = 0,
    limit: int = 100,
    database: Session = Depends(get_db),
    current_admin: User = Depends(require_role(UserRole.ADMIN)),
) -> DocumentListResponse:
    docs, total = DocumentService.list_documents(database, skip=skip, limit=limit)
    return DocumentListResponse(
        documents=[DocumentResponse.model_validate(doc) for doc in docs],
        total=total,
    )


@router.get(
    "/{document_id}",
    response_model=DocumentDetailResponse,
    summary="Get document details and chunks",
    description="Returns the detailed metadata of a specific document including its extracted chunks. (Admin only)",
)
def get_document(
    document_id: UUID,
    database: Session = Depends(get_db),
    current_admin: User = Depends(require_role(UserRole.ADMIN)),
) -> DocumentDetailResponse:
    document = DocumentService.get_document(database, document_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{document_id}' not found",
        )
    return DocumentDetailResponse.model_validate(document)


@router.delete(
    "/{document_id}",
    summary="Delete a document and its chunks",
    description="Deletes document metadata, database chunks, and local storage file. (Admin only)",
)
def delete_document(
    document_id: UUID,
    database: Session = Depends(get_db),
    current_admin: User = Depends(require_role(UserRole.ADMIN)),
) -> dict[str, str]:
    success = DocumentService.delete_document(database, document_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{document_id}' not found",
        )
    return {"status": "deleted", "document_id": str(document_id)}
