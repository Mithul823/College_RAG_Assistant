from typing import Any

from app.rag.retrieval.retriever import RetrievedChunk

DEFAULT_SYSTEM_PROMPT = """You are an accurate, evidence-grounded institutional assistant.

Your task is to answer the user's question using ONLY the provided retrieved context.

Rules:
1. Provide the exact factual answer, numbers, percentages, dates, course codes, and requirements directly from the retrieved context.
2. Quote or state specific rules, policies, and details directly from the text.
3. Do not invent or extrapolate any information not found in the context.
4. If the retrieved context does not contain the answer, respond with: "I couldn't find reliable information about this in the college knowledge base."
5. Format the answer cleanly using clear paragraphs or bullet points for readability."""


class PromptBuilder:
    """Constructs structured RAG prompts and formatted source contexts."""

    @staticmethod
    def format_context(chunks: list[RetrievedChunk]) -> str:
        """Format retrieved chunks into a standardized context block."""
        if not chunks:
            return "No relevant context retrieved."

        sources: list[str] = []
        for index, chunk in enumerate(chunks, start=1):
            header_lines = [
                f"SOURCE {index}",
                f"Document: {chunk.document_name}",
                f"Page: {chunk.page_number}",
            ]
            if chunk.section:
                header_lines.append(f"Section: {chunk.section}")
            if chunk.department:
                header_lines.append(f"Department: {chunk.department}")

            header = "\n".join(header_lines)
            sources.append(f"{header}\n\n{chunk.text.strip()}")

        return "\n\n---\n\n".join(sources)

    @classmethod
    def build_user_prompt(
        cls,
        question: str,
        chunks: list[RetrievedChunk],
        conversation_history: list[dict[str, str]] | None = None,
    ) -> str:
        """Construct the full prompt payload including context and conversation history."""
        context_block = cls.format_context(chunks)

        history_block = ""
        if conversation_history:
            formatted_turns: list[str] = []
            for turn in conversation_history:
                role = turn.get("role", "user").capitalize()
                content = turn.get("content", "").strip()
                formatted_turns.append(f"{role}: {content}")
            if formatted_turns:
                history_block = "CONVERSATION HISTORY:\n" + "\n".join(formatted_turns) + "\n\n"

        prompt = (
            f"RETRIEVED CONTEXT:\n{context_block}\n\n"
            f"{history_block}"
            f"QUESTION: {question.strip()}\n\n"
            f"ANSWER:"
        )
        return prompt
