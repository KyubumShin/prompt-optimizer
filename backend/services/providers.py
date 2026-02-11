from __future__ import annotations

import logging
from dataclasses import dataclass
from openai import AsyncOpenAI

from ..config import Settings
from .llm_client import LLMClient, AnthropicLLMClient, create_llm_client

logger = logging.getLogger(__name__)

# Hardcoded Anthropic models (no filterable list endpoint)
ANTHROPIC_MODELS = [
    "claude-sonnet-4-5-20250929",
    "claude-haiku-4-5-20251001",
    "claude-opus-4-20250514",
    "claude-3-5-sonnet-20241022",
    "claude-3-5-haiku-20241022",
    "claude-3-haiku-20240307",
]


@dataclass
class ProviderConfig:
    id: str
    name: str
    api_key: str | None
    base_url: str | None
    provider_type: str  # "openai_compatible" | "anthropic"
    configured: bool


def _normalize_model_id(model_id: str) -> str:
    """Strip provider prefixes like 'models/' from model IDs."""
    if model_id.startswith("models/"):
        return model_id[len("models/"):]
    return model_id


def _is_chat_model(model_id: str) -> bool:
    """Check if a model ID appears to be a chat completion model."""
    exclude_keywords = [
        "embed", "tts", "whisper", "dall-e", "moderation",
        "imagen", "veo", "lyria", "generate", "audio", "robotics",
        "image", "deep-research",
    ]
    model_lower = model_id.lower()
    if model_lower in ("aqa",):
        return False
    return not any(keyword in model_lower for keyword in exclude_keywords)


class ProviderRegistry:
    """Registry of configured LLM providers."""

    def __init__(self, settings: Settings):
        self._settings = settings
        self._providers: dict[str, ProviderConfig] = {}
        self._build(settings)

    def _build(self, settings: Settings):
        for p in settings.get_providers():
            self._providers[p["id"]] = ProviderConfig(
                id=p["id"],
                name=p["name"],
                api_key=p["api_key"],
                base_url=p["base_url"],
                provider_type=p["provider_type"],
                configured=p["configured"],
            )

    def list_providers(self) -> list[dict]:
        """Return provider metadata (without secrets)."""
        return [
            {"id": p.id, "name": p.name, "configured": p.configured}
            for p in self._providers.values()
        ]

    def get_provider(self, provider_id: str) -> ProviderConfig | None:
        return self._providers.get(provider_id)

    def get_client(self, provider_id: str) -> LLMClient | AnthropicLLMClient:
        """Create an LLM client for the given provider."""
        provider = self._providers.get(provider_id)
        if not provider or not provider.configured or not provider.api_key:
            raise ValueError(f"Provider '{provider_id}' is not configured")
        return create_llm_client(provider.provider_type, provider.api_key, provider.base_url)

    def get_client_for_custom(self, base_url: str, api_key: str | None = None) -> LLMClient:
        """Create an LLM client for a custom endpoint."""
        key = api_key or self._settings.OPENAI_API_KEY
        return LLMClient(api_key=key, base_url=base_url)

    async def list_models(self, provider_id: str) -> list[str]:
        """Fetch available models for a provider."""
        provider = self._providers.get(provider_id)
        if not provider or not provider.configured:
            return []

        if provider.provider_type == "anthropic":
            return list(ANTHROPIC_MODELS)

        # OpenAI-compatible: fetch from API
        if not provider.api_key:
            return []
        try:
            client = AsyncOpenAI(api_key=provider.api_key, base_url=provider.base_url)
            models_list = await client.models.list()
            chat_models = [
                _normalize_model_id(m.id) for m in models_list.data
                if _is_chat_model(_normalize_model_id(m.id))
            ]
            chat_models.sort()
            return chat_models
        except Exception as e:
            logger.warning(f"Failed to fetch models for {provider_id}: {e}")
            raise

    async def list_custom_models(self, base_url: str, api_key: str | None = None) -> list[str]:
        """Fetch models from a custom OpenAI-compatible endpoint."""
        key = api_key or self._settings.OPENAI_API_KEY
        client = AsyncOpenAI(api_key=key, base_url=base_url)
        models_list = await client.models.list()
        chat_models = [
            _normalize_model_id(m.id) for m in models_list.data
            if _is_chat_model(_normalize_model_id(m.id))
        ]
        chat_models.sort()
        return chat_models

    def get_defaults(self) -> dict:
        """Return default provider+model for each pipeline stage."""
        default_provider = self._settings.get_default_provider()
        return {
            "model": self._settings.OPENAI_MODEL,
            "model_provider": default_provider,
            "judge_model": self._settings.JUDGE_MODEL,
            "judge_provider": default_provider,
            "improver_model": self._settings.IMPROVER_MODEL,
            "improver_provider": default_provider,
        }
