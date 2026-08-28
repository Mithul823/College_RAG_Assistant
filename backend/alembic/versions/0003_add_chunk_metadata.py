"""store ingestion metadata on document chunks

Revision ID: 0003_add_chunk_metadata
Revises: 0002_create_documents_and_chunks
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "0003_add_chunk_metadata"
down_revision: str | None = "0002_create_documents_and_chunks"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "document_chunks",
        sa.Column("document_name", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "document_chunks",
        sa.Column("department", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "document_chunks",
        sa.Column("academic_year", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "document_chunks",
        sa.Column("semester", sa.String(length=50), nullable=True),
    )

    op.execute(
        "UPDATE document_chunks SET document_name = "
        "(SELECT filename FROM documents WHERE documents.id = document_chunks.document_id)"
    )
    op.alter_column("document_chunks", "document_name", nullable=False)


def downgrade() -> None:
    op.drop_column("document_chunks", "semester")
    op.drop_column("document_chunks", "academic_year")
    op.drop_column("document_chunks", "department")
    op.drop_column("document_chunks", "document_name")