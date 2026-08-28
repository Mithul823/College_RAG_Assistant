from dataclasses import dataclass
import re
from typing import Any
from uuid import UUID, uuid4


@dataclass
class ChunkMetadata:
    document_id: UUID
    chunk_id: UUID
    chunk_index: int
    document_name: str
    page_number: int
    section: str | None
    department: str | None
    academic_year: str | None
    semester: str | None
    token_count: int


@dataclass
class ProcessedChunk:
    id: UUID
    document_id: UUID
    chunk_index: int
    page_number: int
    section: str | None
    text: str
    token_count: int
    metadata: dict[str, Any]


class PageAwareChunker:
    """Page-aware, section-sensitive text chunker."""

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50) -> None:
        """Initialize chunker with target chunk size and overlap in approximate tokens.

        Note: Approximates 1 token ~= 0.75 words or ~4 characters.
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """Estimate token count from whitespace-split words and characters."""
        if not text:
            return 0
        words = text.split()
        # Common rule of thumb: max of (words / 0.75) and (characters / 4)
        return max(int(len(words) / 0.75), int(len(text) / 4))

    @staticmethod
    def _is_heading(line: str) -> bool:
        """Heuristic to detect section headings."""
        stripped = line.strip()
        if not stripped or len(stripped) > 120:
            return False

        # Markdown headings
        if stripped.startswith("#"):
            return True

        # Numbered sections like "1. Introduction", "Section 3.2", "Chapter IV"
        if re.match(r"^(section|chapter|part|article|\d+(\.\d+)*)\b", stripped, re.IGNORECASE):
            return True

        # Short uppercase or title-like lines that do not end in a period
        if len(stripped) < 60 and not stripped.endswith((".", ":", ";", ",")):
            if stripped.isupper() or stripped.istitle():
                return True

        return False

    def _split_into_paragraphs(self, text: str) -> list[str]:
        """Split text by double newlines into paragraphs."""
        return [p.strip() for p in text.split("\n\n") if p.strip()]

    def _split_into_sentences(self, paragraph: str) -> list[str]:
        """Split paragraph into sentence units."""
        sentences = re.split(r"(?<=[.!?])\s+", paragraph)
        return [s.strip() for s in sentences if s.strip()]

    def chunk_document(
        self,
        pages: list[dict[str, Any]],
        document_id: UUID,
        document_name: str,
        department: str | None = None,
        academic_year: str | None = None,
        semester: str | None = None,
    ) -> list[ProcessedChunk]:
        """Chunk document pages with page preservation and rich metadata.

        Args:
            pages: List of dicts with 'page_number' and 'text'.
            document_id: Unique UUID of the document.
            document_name: Filename or title of the document.
            department: Associated department metadata.
            academic_year: Academic year metadata.
            semester: Semester metadata.

        Returns:
            List of ProcessedChunk objects.
        """
        chunks: list[ProcessedChunk] = []
        global_chunk_index = 0
        current_section: str | None = None

        for page in pages:
            page_num = page.get("page_number", 1)
            raw_page_text = page.get("text", "")

            if not raw_page_text.strip():
                continue

            paragraphs = self._split_into_paragraphs(raw_page_text)
            current_buffer: list[str] = []
            current_tokens = 0

            for paragraph in paragraphs:
                # Check for section heading update
                first_line = paragraph.split("\n")[0]
                if self._is_heading(first_line):
                    current_section = first_line.lstrip("#").strip()

                para_tokens = self._estimate_tokens(paragraph)

                # If single paragraph exceeds chunk size, split by sentences
                if para_tokens > self.chunk_size:
                    sentences = self._split_into_sentences(paragraph)
                    for sentence in sentences:
                        sent_tokens = self._estimate_tokens(sentence)
                        if current_tokens + sent_tokens > self.chunk_size and current_buffer:
                            chunk_text = " ".join(current_buffer)
                            chunk_id = uuid4()
                            token_cnt = self._estimate_tokens(chunk_text)
                            chunks.append(
                                ProcessedChunk(
                                    id=chunk_id,
                                    document_id=document_id,
                                    chunk_index=global_chunk_index,
                                    page_number=page_num,
                                    section=current_section,
                                    text=chunk_text,
                                    token_count=token_cnt,
                                    metadata={
                                        "document_id": str(document_id),
                                        "chunk_id": str(chunk_id),
                                        "chunk_index": global_chunk_index,
                                        "document_name": document_name,
                                        "page_number": page_num,
                                        "section": current_section,
                                        "department": department,
                                        "academic_year": academic_year,
                                        "semester": semester,
                                    },
                                )
                            )
                            global_chunk_index += 1

                            # Overlap buffer from tail
                            overlap_tokens = 0
                            new_buffer: list[str] = []
                            for prev_sent in reversed(current_buffer):
                                prev_tokens = self._estimate_tokens(prev_sent)
                                if overlap_tokens + prev_tokens <= self.chunk_overlap:
                                    new_buffer.insert(0, prev_sent)
                                    overlap_tokens += prev_tokens
                                else:
                                    break
                            current_buffer = new_buffer
                            current_tokens = overlap_tokens

                        current_buffer.append(sentence)
                        current_tokens += sent_tokens
                else:
                    if current_tokens + para_tokens > self.chunk_size and current_buffer:
                        chunk_text = "\n\n".join(current_buffer)
                        chunk_id = uuid4()
                        token_cnt = self._estimate_tokens(chunk_text)
                        chunks.append(
                            ProcessedChunk(
                                id=chunk_id,
                                document_id=document_id,
                                chunk_index=global_chunk_index,
                                page_number=page_num,
                                section=current_section,
                                text=chunk_text,
                                token_count=token_cnt,
                                metadata={
                                    "document_id": str(document_id),
                                    "chunk_id": str(chunk_id),
                                    "chunk_index": global_chunk_index,
                                    "document_name": document_name,
                                    "page_number": page_num,
                                    "section": current_section,
                                    "department": department,
                                    "academic_year": academic_year,
                                    "semester": semester,
                                },
                            )
                        )
                        global_chunk_index += 1

                        # Simple overlap: carry over the last paragraph if under overlap budget
                        last_para = current_buffer[-1]
                        last_para_tokens = self._estimate_tokens(last_para)
                        if last_para_tokens <= self.chunk_overlap:
                            current_buffer = [last_para]
                            current_tokens = last_para_tokens
                        else:
                            current_buffer = []
                            current_tokens = 0

                    current_buffer.append(paragraph)
                    current_tokens += para_tokens

            # Flush remaining buffer for this page
            if current_buffer:
                chunk_text = "\n\n".join(current_buffer)
                chunk_id = uuid4()
                token_cnt = self._estimate_tokens(chunk_text)
                chunks.append(
                    ProcessedChunk(
                        id=chunk_id,
                        document_id=document_id,
                        chunk_index=global_chunk_index,
                        page_number=page_num,
                        section=current_section,
                        text=chunk_text,
                        token_count=token_cnt,
                        metadata={
                            "document_id": str(document_id),
                            "chunk_id": str(chunk_id),
                            "chunk_index": global_chunk_index,
                            "document_name": document_name,
                            "page_number": page_num,
                            "section": current_section,
                            "department": department,
                            "academic_year": academic_year,
                            "semester": semester,
                        },
                    )
                )
                global_chunk_index += 1

        return chunks

