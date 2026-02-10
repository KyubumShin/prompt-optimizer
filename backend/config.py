from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    OPENAI_API_KEY: str
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-4o-mini"
    JUDGE_MODEL: str = "gpt-4o-mini"
    IMPROVER_MODEL: str = "gpt-4o"
    DATABASE_URL: str = "sqlite+aiosqlite:///./prompt_optimizer.db"
    DEFAULT_CONCURRENCY: int = 5
    DEFAULT_MAX_ITERATIONS: int = 10
    DEFAULT_TARGET_SCORE: float = 0.9
    DEFAULT_TEMPERATURE: float = 0.7
    CONVERGENCE_THRESHOLD: float = 0.02
    CONVERGENCE_PATIENCE: int = 2

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


def get_settings() -> Settings:
    return Settings()

settings = get_settings()
