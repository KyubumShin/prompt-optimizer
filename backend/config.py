from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Legacy keys (backward compatible - may point to any provider)
    OPENAI_API_KEY: str
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-4o-mini"
    JUDGE_MODEL: str = "gpt-4o-mini"
    IMPROVER_MODEL: str = "gpt-4o"

    # Provider-specific keys (all optional)
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    ANTHROPIC_API_KEY: Optional[str] = None
    OPENAI_PROVIDER_API_KEY: Optional[str] = None
    OPENAI_PROVIDER_BASE_URL: str = "https://api.openai.com/v1"

    DATABASE_URL: str = "sqlite+aiosqlite:///./prompt_optimizer.db"
    DEFAULT_CONCURRENCY: int = 5
    DEFAULT_MAX_ITERATIONS: int = 10
    DEFAULT_TARGET_SCORE: float = 0.9
    DEFAULT_TEMPERATURE: float = 0.7
    CONVERGENCE_THRESHOLD: float = 0.02
    CONVERGENCE_PATIENCE: int = 2

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    def _is_legacy_gemini(self) -> bool:
        """Check if legacy OPENAI_BASE_URL points to Gemini."""
        return "generativelanguage.googleapis.com" in self.OPENAI_BASE_URL

    def get_providers(self) -> list[dict]:
        """Return list of configured providers based on env vars."""
        providers = []

        # Gemini: explicit key or legacy key pointing to Gemini
        gemini_key = self.GEMINI_API_KEY
        if not gemini_key and self._is_legacy_gemini():
            gemini_key = self.OPENAI_API_KEY
        providers.append({
            "id": "gemini",
            "name": "Google Gemini",
            "configured": gemini_key is not None,
            "api_key": gemini_key,
            "base_url": self.GEMINI_BASE_URL,
            "provider_type": "openai_compatible",
        })

        # OpenAI: explicit provider key or legacy key (if not pointing to Gemini)
        openai_key = self.OPENAI_PROVIDER_API_KEY
        if not openai_key and not self._is_legacy_gemini():
            openai_key = self.OPENAI_API_KEY
        providers.append({
            "id": "openai",
            "name": "OpenAI",
            "configured": openai_key is not None,
            "api_key": openai_key,
            "base_url": self.OPENAI_PROVIDER_BASE_URL,
            "provider_type": "openai_compatible",
        })

        # Anthropic
        providers.append({
            "id": "anthropic",
            "name": "Anthropic",
            "configured": self.ANTHROPIC_API_KEY is not None,
            "api_key": self.ANTHROPIC_API_KEY,
            "base_url": None,
            "provider_type": "anthropic",
        })

        # Custom (always shown, never pre-configured)
        providers.append({
            "id": "custom",
            "name": "Custom Endpoint",
            "configured": False,
            "api_key": None,
            "base_url": None,
            "provider_type": "openai_compatible",
        })

        return providers

    def get_default_provider(self) -> str:
        """Return the default provider ID based on legacy config."""
        if self._is_legacy_gemini():
            return "gemini"
        return "openai"


def get_settings() -> Settings:
    return Settings()

settings = get_settings()
