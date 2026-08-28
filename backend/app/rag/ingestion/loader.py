import io
from pathlib import Path
from typing import Any

from pypdf import PdfReader


class PDFValidationError(Exception):
    """Raised when PDF file validation fails."""


class PDFExtractionError(Exception):
    """Raised when text extraction from PDF fails."""


class PDFLoader:
    """Validates PDF files and extracts text page-by-page."""

    @staticmethod
    def validate_pdf(
        content: bytes,
        content_type: str | None = None,
        max_size_mb: int = 20,
    ) -> None:
        """Validate PDF magic bytes, MIME type, and file size.

        Raises:
            PDFValidationError: If validation fails.
        """
        max_size_bytes = max_size_mb * 1024 * 1024
        if len(content) > max_size_bytes:
            raise PDFValidationError(
                f"File size ({len(content) / (1024 * 1024):.2f} MB) exceeds limit of {max_size_mb} MB"
            )

        valid_mimes = (
            "application/pdf",
            "application/x-pdf",
            "application/acrobat",
            "applications/vnd.pdf",
            "text/pdf",
            "text/x-pdf",
            "application/octet-stream",
            "binary/octet-stream",
        )
        if content_type:
            cleaned_type = content_type.lower().split(";")[0].strip()
            if cleaned_type and not any(cleaned_type == m for m in valid_mimes):
                raise PDFValidationError(f"Invalid content type '{content_type}', expected 'application/pdf'")

        if not content.startswith(b"%PDF-"):
            raise PDFValidationError("Invalid file signature: File is not a valid PDF document")

    @classmethod
    def extract_pages(cls, source: bytes | str | Path) -> list[dict[str, Any]]:
        """Extract text from a PDF source on a page-by-page basis.

        Args:
            source: Raw bytes or file path of the PDF.

        Returns:
            List of dictionaries with 'page_number' (1-indexed) and 'text'.

        Raises:
            PDFExtractionError: If PDF is encrypted, corrupted, or cannot be read.
        """
        try:
            if isinstance(source, bytes):
                stream = io.BytesIO(source)
                reader = PdfReader(stream)
            else:
                reader = PdfReader(str(source))

            if reader.is_encrypted:
                try:
                    # Attempt decrypt with empty password for read-protected without password
                    reader.decrypt("")
                except Exception as exc:
                    raise PDFExtractionError("Encrypted PDF documents are not supported") from exc

            pages: list[dict[str, Any]] = []
            for index, page in enumerate(reader.pages):
                page_text = page.extract_text() or ""
                pages.append({"page_number": index + 1, "text": page_text})

            if not pages:
                raise PDFExtractionError("The PDF document does not contain any pages")

            return pages
        except PDFExtractionError:
            raise
        except Exception as exc:
            raise PDFExtractionError(f"Failed to extract text from PDF: {exc}") from exc
