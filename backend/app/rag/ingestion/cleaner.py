import re


class TextCleaner:
    """Non-destructive text cleaner preserving structure, numbers, dates, and course codes."""

    @staticmethod
    def clean_text(text: str) -> str:
        """Clean raw extracted text while preserving semantic structure.

        - Replaces non-standard whitespace and tabs with standard spaces
        - Normalizes Windows CRLF line breaks to LF
        - Collapses 3+ consecutive line breaks into 2 (paragraph boundary)
        - Collapses multiple spaces per line to a single space
        - Strips whitespace per line while preserving paragraphs
        """
        if not text:
            return ""

        # Remove null bytes (which crash PostgreSQL) and normalize line endings
        normalized = text.replace("\x00", "").replace("\r\n", "\n").replace("\r", "\n")
        normalized = normalized.replace("\u00a0", " ").replace("\t", " ")

        # Normalize smart quotes and PDF bullet artifacts
        normalized = normalized.replace("\u201c", '"').replace("\u201d", '"')
        normalized = normalized.replace("\u2018", "'").replace("\u2019", "'")
        normalized = normalized.replace("\u2013", "-").replace("\u2014", "-")
        normalized = normalized.replace("\u2022", "- ").replace("\uf0b7", "- ").replace("\ufffd", "")

        # Process line-by-line: trim lines and remove multi-space sequences
        lines = []
        for line in normalized.split("\n"):
            cleaned_line = re.sub(r"[ ]{2,}", " ", line).strip()
            lines.append(cleaned_line)

        cleaned_text = "\n".join(lines)

        # Collapse more than two consecutive newlines into exactly two (paragraph separation)
        cleaned_text = re.sub(r"\n{3,}", "\n\n", cleaned_text)

        return cleaned_text.strip()

