from __future__ import annotations

import asyncio
import json
import re
import logging
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

class LLMClient:
    def __init__(self, api_key: str, base_url: str = "https://api.openai.com/v1"):
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    async def complete(self, prompt: str, model: str, temperature: float = 0.7, system_prompt: str | None = None, max_retries: int = 5) -> str:
        """Call LLM with exponential backoff retry (2s -> 4s -> 8s...)"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        for attempt in range(max_retries):
            try:
                response = await self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                )
                return response.choices[0].message.content or ""
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                wait = 2 ** (attempt + 1)
                logger.warning(f"LLM call failed (attempt {attempt+1}/{max_retries}): {e}. Retrying in {wait}s")
                await asyncio.sleep(wait)
        return ""

    async def complete_json(self, prompt: str, model: str, temperature: float = 0.7, system_prompt: str | None = None) -> dict:
        """Call LLM and parse JSON response. Strips markdown code blocks, uses regex fallback."""
        raw = await self.complete(prompt, model, temperature, system_prompt)
        return self._parse_json(raw)

    @staticmethod
    def _parse_json(text: str) -> dict:
        # Strip markdown code blocks
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
