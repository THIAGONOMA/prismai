from __future__ import annotations

from typing import Any


def criar_llm(
    model: str = "gpt-4o-mini",
    temperature: float = 0,
    timeout: int = 60,
) -> Any:
    """Factory that routes to the right provider by model slug prefix."""
    if model.startswith("claude"):
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(model=model, temperature=temperature, timeout=timeout, max_retries=0)

    from langchain_openai import ChatOpenAI

    return ChatOpenAI(model=model, temperature=temperature, timeout=timeout, max_retries=0)
