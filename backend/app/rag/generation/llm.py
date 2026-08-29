from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from functools import lru_cache
import logging
import re
from typing import Any

import httpx

from app.core.config import get_settings
from app.rag.generation.prompt import DEFAULT_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

UNKNOWN_ANSWER_TEXT = "I couldn't find reliable information about this in the college knowledge base."


@dataclass
class LLMResult:
    answer: str
    source_chunk_ids: list[str] = field(default_factory=list)
    answer_mode: str = "grounded"  # "grounded", "unknown", "error"


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def generate_response(
        self,
        prompt: str,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        source_chunk_ids: list[str] | None = None,
    ) -> LLMResult:
        """Generate a response for the user prompt."""
        pass


class MockLLMProvider(LLMProvider):
    """Local extractive RAG generator that extracts exact factual answers directly from retrieved PDF context."""

    @staticmethod
    def _extract_exact_answer(prompt: str) -> str:
        if not prompt or not prompt.strip():
            return UNKNOWN_ANSWER_TEXT

        if "RETRIEVED CONTEXT:" in prompt:
            context_part = prompt.split("RETRIEVED CONTEXT:")[1]
            if "CONVERSATION HISTORY:" in context_part:
                context_part = context_part.split("CONVERSATION HISTORY:")[0]
            elif "QUESTION:" in context_part:
                context_part = context_part.split("QUESTION:")[0]
        else:
            context_part = prompt

        context_part = context_part.strip()
        if not context_part or "No relevant context retrieved" in context_part:
            return UNKNOWN_ANSWER_TEXT

        # Parse question if present
        question = ""
        if "QUESTION:" in prompt:
            question = prompt.split("QUESTION:")[1].split("ANSWER:")[0].strip()

        # Split into distinct source sections
        blocks = context_part.split("---")
        extracted_sections: list[str] = []

        q_words = [
            w.lower().strip(".,!?:;\"'()[]{}")
            for w in question.split()
            if len(w.strip(".,!?:;\"'()[]{}")) > 2
        ]
        stopwords = {
            "what", "when", "where", "which", "who", "whom", "whose", "why", "how",
            "is", "are", "was", "were", "the", "for", "and", "tell", "about", "can",
            "you", "give", "please", "does", "have", "with", "from", "show", "policy", "requirements"
        }
        core_terms = [w for w in q_words if w not in stopwords]

        for block in blocks:
            raw_lines = [l.strip() for l in block.strip().split("\n") if l.strip()]
            body_lines = []
            for line in raw_lines:
                if (
                    not line.startswith("SOURCE")
                    and not line.startswith("Document:")
                    and not line.startswith("Page:")
                    and not line.startswith("Section:")
                    and not line.startswith("Department:")
                ):
                    body_lines.append(line)

            content_text = "\n".join(body_lines).strip()
            if not content_text:
                continue

            # Check if this content is directly relevant to question terms
            content_lower = content_text.lower()
            if core_terms:
                matching_terms = [t for t in core_terms if t in content_lower]
                if matching_terms:
                    extracted_sections.append(content_text)
            else:
                extracted_sections.append(content_text)

        if not extracted_sections:
            # Return full content from the highest ranking retrieved source
            first_block = blocks[0].strip()
            lines = [
                l.strip()
                for l in first_block.split("\n")
                if l.strip()
                and not l.startswith("SOURCE")
                and not l.startswith("Document:")
                and not l.startswith("Page:")
                and not l.startswith("Section:")
                and not l.startswith("Department:")
            ]
            first_content = "\n".join(lines).strip()
            if first_content:
                return first_content
            return context_part

        # Combine matching text sections cleanly
        combined = "\n\n".join(dict.fromkeys(extracted_sections))
        return combined

    async def generate_response(
        self,
        prompt: str,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        source_chunk_ids: list[str] | None = None,
    ) -> LLMResult:
        chunk_ids = source_chunk_ids or []
        if not chunk_ids or "No relevant context retrieved" in prompt:
            return LLMResult(
                answer=UNKNOWN_ANSWER_TEXT,
                source_chunk_ids=[],
                answer_mode="unknown",
            )

        exact_answer = self._extract_exact_answer(prompt)
        if exact_answer == UNKNOWN_ANSWER_TEXT:
            return LLMResult(
                answer=UNKNOWN_ANSWER_TEXT,
                source_chunk_ids=[],
                answer_mode="unknown",
            )

        return LLMResult(
            answer=exact_answer,
            source_chunk_ids=chunk_ids,
            answer_mode="grounded",
        )


class GeminiLLMProvider(LLMProvider):
    """Provider for Google's Gemini generateContent API."""

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        settings = get_settings()
        self.api_key = api_key or settings.gemini_api_key or settings.llm_api_key
        self.model = model or settings.llm_model or "gemini-2.0-flash"

    async def generate_response(
        self,
        prompt: str,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        source_chunk_ids: list[str] | None = None,
    ) -> LLMResult:
        chunk_ids = source_chunk_ids or []
        if not self.api_key or self.api_key == "CHANGE_ME":
            logger.warning("gemini_api_key_not_configured_falling_back_to_mock")
            return await MockLLMProvider().generate_response(prompt, system_prompt, chunk_ids)

        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent"
        )
        payload = {
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.1},
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    url,
                    params={"key": self.api_key},
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                answer = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                return LLMResult(
                    answer=answer,
                    source_chunk_ids=chunk_ids,
                    answer_mode="grounded",
                )
        except Exception as exc:
            logger.error("gemini_llm_generation_failed", extra={"error": str(exc)})
            return await MockLLMProvider().generate_response(prompt, system_prompt, chunk_ids)


class OpenAILLMProvider(LLMProvider):
    """Provider for OpenAI and OpenAI-compatible Chat Completion APIs."""

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        settings = get_settings()
        self.api_key = api_key or settings.llm_api_key
        self.model = model or settings.llm_model or "gpt-4o-mini"

    async def generate_response(
        self,
        prompt: str,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        source_chunk_ids: list[str] | None = None,
    ) -> LLMResult:
        chunk_ids = source_chunk_ids or []
        if not self.api_key or self.api_key == "CHANGE_ME":
            logger.warning("llm_api_key_not_configured_falling_back_to_mock")
            return await MockLLMProvider().generate_response(prompt, system_prompt, chunk_ids)

        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                answer = data["choices"][0]["message"]["content"].strip()
                return LLMResult(
                    answer=answer,
                    source_chunk_ids=chunk_ids,
                    answer_mode="grounded",
                )
        except Exception as exc:
            logger.error("openai_llm_generation_failed", extra={"error": str(exc)})
            return await MockLLMProvider().generate_response(prompt, system_prompt, chunk_ids)


@lru_cache
def get_llm_provider() -> LLMProvider:
    """Return configured LLM provider singleton."""
    settings = get_settings()
    provider_name = settings.llm_provider.lower().strip()
    has_gemini_key = bool((settings.gemini_api_key or settings.llm_api_key) and (settings.gemini_api_key != "CHANGE_ME" and settings.llm_api_key != "CHANGE_ME"))

    if provider_name == "gemini" or has_gemini_key:
        return GeminiLLMProvider()

    if provider_name in ("openai", "azure"):
        return OpenAILLMProvider()

    # Default to mock provider if provider is not configured or set to mock/change_me
    return MockLLMProvider()
