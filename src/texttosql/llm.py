"""Gemini model factory.

Two tiers:
  * "main" (default gemini-2.5-pro)  -> SQL generation + self-correction (needs reasoning)
  * "fast" (default gemini-2.5-flash) -> routing, intent, answer synthesis (cheap/quick)
"""

from __future__ import annotations

from functools import lru_cache

from langchain_google_genai import ChatGoogleGenerativeAI

from .config import get_settings


@lru_cache
def get_llm(tier: str = "main", temperature: float = 0.0) -> ChatGoogleGenerativeAI:
    """Return a cached Gemini chat model for the given tier ("main" | "fast")."""
    settings = get_settings()
    if not settings.google_api_key:
        raise RuntimeError(
            "GOOGLE_API_KEY is not set. Copy .env.example to .env and fill it in."
        )

    model = settings.gemini_model_main if tier == "main" else settings.gemini_model_fast
    return ChatGoogleGenerativeAI(
        model=model,
        google_api_key=settings.google_api_key,
        temperature=temperature,
        # Deterministic-ish SQL: keep top-p tight and cap output size.
        max_output_tokens=2048,
    )
