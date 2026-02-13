from __future__ import annotations

import abc
import asyncio
import json
import re
import logging
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

MAX_RETRIES = 5


async def _retry_with_backoff(fn, max_retries: int = MAX_RETRIES, label: str = "LLM") -> str:
    """Execute an async callable with exponential backoff retry (2s -> 4s -> 8s...).

    The callable should return a str on success and raise on failure.
    """
    for attempt in range(max_retries):
        try:
            return await fn()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            wait = 2 ** (attempt + 1)
            logger.warning(f"{label} call failed (attempt {attempt+1}/{max_retries}): {e}. Retrying in {wait}s")
            await asyncio.sleep(wait)
    return ""


def _parse_json(text: str) -> dict:
    """Parse a JSON response from an LLM, stripping markdown code blocks with regex fallback."""
    cleaned = re.sub(r'^```(?:json)?\s*\n?', '', text.strip())
    cleaned = re.sub(r'\n?```\s*$', '', cleaned)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Regex fallback: find first { ... } block
        match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        return {"error": "Failed to parse JSON", "raw": text}


class BaseLLMClient(abc.ABC):
    """Abstract base class defining the LLM client interface."""

    @abc.abstractmethod
    async def complete(self, prompt: str, model: str, temperature: float = 0.7, system_prompt: str | None = None, max_retries: int = MAX_RETRIES) -> str:
        """Send a prompt and return the text response."""
        ...

    async def complete_json(self, prompt: str, model: str, temperature: float = 0.7, system_prompt: str | None = None) -> dict:
        """Call LLM and parse JSON response. Strips markdown code blocks, uses regex fallback."""
        raw = await self.complete(prompt, model, temperature, system_prompt)
        return _parse_json(raw)


class LLMClient(BaseLLMClient):
    """OpenAI-compatible LLM client with retry logic."""

    def __init__(self, api_key: str, base_url: str = "https://api.openai.com/v1"):
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    async def complete(self, prompt: str, model: str, temperature: float = 0.7, system_prompt: str | None = None, max_retries: int = MAX_RETRIES) -> str:
        """Call LLM with exponential backoff retry."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        async def _call():
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
            )
            return response.choices[0].message.content or ""

        return await _retry_with_backoff(_call, max_retries, label="LLM")

    # Keep static method for backward compatibility with tests
    _parse_json = staticmethod(_parse_json)


class AnthropicLLMClient(BaseLLMClient):
    """Anthropic SDK client with the same interface as LLMClient."""

    ANTHROPIC_MAX_TOKENS = 4096

    def __init__(self, api_key: str):
        from anthropic import AsyncAnthropic
        self.client = AsyncAnthropic(api_key=api_key)

    async def complete(self, prompt: str, model: str, temperature: float = 0.7, system_prompt: str | None = None, max_retries: int = MAX_RETRIES) -> str:
        """Call Anthropic API with exponential backoff retry."""

        async def _call():
            kwargs: dict = {
                "model": model,
                "max_tokens": self.ANTHROPIC_MAX_TOKENS,
                "temperature": temperature,
                "messages": [{"role": "user", "content": prompt}],
            }
            if system_prompt:
                kwargs["system"] = system_prompt

            response = await self.client.messages.create(**kwargs)
            text_parts = []
            for block in response.content:
                if block.type == "text":
                    text_parts.append(block.text)
            return "".join(text_parts)

        return await _retry_with_backoff(_call, max_retries, label="Anthropic")


def create_llm_client(provider_type: str, api_key: str, base_url: str | None = None) -> BaseLLMClient:
    """Factory function to create the appropriate LLM client."""
    if provider_type == "anthropic":
        return AnthropicLLMClient(api_key=api_key)
    else:
        return LLMClient(api_key=api_key, base_url=base_url or "https://api.openai.com/v1")
