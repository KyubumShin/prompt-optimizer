"""Shared test fixtures for prompt-optimizer unit tests."""
from __future__ import annotations

import os
import pytest


@pytest.fixture
def make_settings():
    """Factory fixture to create Settings with arbitrary env var overrides."""
    def _make(**overrides):
        from backend.config import Settings
        defaults = {
            "OPENAI_API_KEY": "test-key",
            "OPENAI_BASE_URL": "https://api.openai.com/v1",
        }
        defaults.update(overrides)
        return Settings(**defaults)
    return _make


@pytest.fixture
def make_registry():
    """Factory fixture to create a ProviderRegistry with arbitrary settings."""
    def _make(**overrides):
        from backend.config import Settings
        from backend.services.providers import ProviderRegistry
        defaults = {
            "OPENAI_API_KEY": "test-key",
            "OPENAI_BASE_URL": "https://api.openai.com/v1",
        }
        defaults.update(overrides)
        settings = Settings(**defaults)
        return ProviderRegistry(settings)
    return _make


@pytest.fixture
def app_client():
    """FastAPI TestClient with test environment defaults."""
    os.environ.setdefault("OPENAI_API_KEY", "test-key")
    os.environ.setdefault("OPENAI_BASE_URL", "https://api.openai.com/v1")
    from fastapi.testclient import TestClient
    from backend.main import app
    return TestClient(app)
