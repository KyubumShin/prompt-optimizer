from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ..config import Settings, get_settings
from ..services.providers import ProviderRegistry

router = APIRouter(prefix="/api/providers", tags=["providers"])


def _get_registry(settings: Settings = Depends(get_settings)) -> ProviderRegistry:
    return ProviderRegistry(settings)


class CustomModelsRequest(BaseModel):
    base_url: str
    api_key: Optional[str] = None


@router.get("")
async def get_providers(registry: ProviderRegistry = Depends(_get_registry)):
    """List all providers with configuration status and defaults."""
    return {
        "providers": registry.list_providers(),
        "defaults": registry.get_defaults(),
    }


@router.get("/{provider_id}/models")
async def get_provider_models(provider_id: str, registry: ProviderRegistry = Depends(_get_registry)):
    """Fetch available models for a specific provider."""
    provider = registry.get_provider(provider_id)
    if not provider:
        return {"models": [], "error": f"Unknown provider: {provider_id}"}
    if not provider.configured:
        return {"models": [], "error": f"Provider '{provider_id}' is not configured. Set the appropriate API key in .env"}
    try:
        models = await registry.list_models(provider_id)
        return {"models": models}
    except Exception as e:
        return {"models": [], "error": str(e)}


@router.post("/custom/models")
async def get_custom_models(body: CustomModelsRequest, registry: ProviderRegistry = Depends(_get_registry)):
    """Fetch models from a custom OpenAI-compatible endpoint."""
    try:
        models = await registry.list_custom_models(body.base_url, body.api_key or None)
        return {"models": models}
    except Exception as e:
        return {"models": [], "error": str(e)}
