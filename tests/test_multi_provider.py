"""Tests for multi-provider LLM architecture.

Uses multi dynamic context: tests cover config, providers, clients,
pipeline routing, schemas, and API endpoints with varied combinations
of settings, provider types, and configurations.
"""
from __future__ import annotations

import pytest
import json

# ─── Config Tests ───────────────────────────────────────────────────────────


class TestSettingsProviderDetection:
    """Test Settings.get_providers() with multiple dynamic contexts."""

    def test_legacy_openai_config(self, make_settings):
        """Legacy config with OpenAI URL -> OpenAI is default provider."""
        s = make_settings()
        assert s.get_default_provider() == "openai"
        providers = s.get_providers()
        openai = next(p for p in providers if p["id"] == "openai")
        assert openai["configured"] is True
        assert openai["api_key"] == "test-key"

    def test_legacy_gemini_config(self, make_settings):
        """Legacy config with Gemini URL -> Gemini is default, OpenAI unconfigured."""
        s = make_settings(
            OPENAI_BASE_URL="https://generativelanguage.googleapis.com/v1beta/openai/"
        )
        assert s.get_default_provider() == "gemini"
        providers = s.get_providers()
        gemini = next(p for p in providers if p["id"] == "gemini")
        openai = next(p for p in providers if p["id"] == "openai")
        assert gemini["configured"] is True
        assert gemini["api_key"] == "test-key"
        assert openai["configured"] is False

    def test_explicit_gemini_key(self, make_settings):
        """Explicit GEMINI_API_KEY takes priority over legacy auto-detect."""
        s = make_settings(GEMINI_API_KEY="gemini-specific-key")
        providers = s.get_providers()
        gemini = next(p for p in providers if p["id"] == "gemini")
        assert gemini["configured"] is True
        assert gemini["api_key"] == "gemini-specific-key"

    def test_explicit_openai_provider_key(self, make_settings):
        """OPENAI_PROVIDER_API_KEY is used when legacy points to Gemini."""
        s = make_settings(
            OPENAI_BASE_URL="https://generativelanguage.googleapis.com/v1beta/openai/",
            OPENAI_PROVIDER_API_KEY="openai-explicit-key",
        )
        providers = s.get_providers()
        openai = next(p for p in providers if p["id"] == "openai")
        assert openai["configured"] is True
        assert openai["api_key"] == "openai-explicit-key"

    def test_anthropic_configured(self, make_settings):
        """Anthropic configured when ANTHROPIC_API_KEY is set."""
        s = make_settings(ANTHROPIC_API_KEY="sk-ant-test")
        providers = s.get_providers()
        anthropic = next(p for p in providers if p["id"] == "anthropic")
        assert anthropic["configured"] is True
        assert anthropic["api_key"] == "sk-ant-test"
        assert anthropic["provider_type"] == "anthropic"

    def test_anthropic_unconfigured(self, make_settings):
        """Anthropic unconfigured by default."""
        s = make_settings()
        providers = s.get_providers()
        anthropic = next(p for p in providers if p["id"] == "anthropic")
        assert anthropic["configured"] is False
        assert anthropic["api_key"] is None

    def test_custom_always_unconfigured(self, make_settings):
        """Custom provider is always listed but never pre-configured."""
        s = make_settings()
        providers = s.get_providers()
        custom = next(p for p in providers if p["id"] == "custom")
        assert custom["configured"] is False
        assert custom["name"] == "Custom Endpoint"

    def test_all_providers_present(self, make_settings):
        """All four providers always present in list."""
        s = make_settings()
        providers = s.get_providers()
        ids = [p["id"] for p in providers]
        assert ids == ["gemini", "openai", "anthropic", "custom"]

    def test_multi_provider_config(self, make_settings):
        """All three real providers configured simultaneously."""
        s = make_settings(
            OPENAI_BASE_URL="https://generativelanguage.googleapis.com/v1beta/openai/",
            GEMINI_API_KEY="gem-key",
            OPENAI_PROVIDER_API_KEY="oai-key",
            ANTHROPIC_API_KEY="ant-key",
        )
        providers = s.get_providers()
        configured = [p for p in providers if p["configured"]]
        assert len(configured) == 3
        assert {p["id"] for p in configured} == {"gemini", "openai", "anthropic"}


# ─── LLM Client Tests ──────────────────────────────────────────────────────


class TestLLMClientFactory:
    """Test create_llm_client with multiple provider types."""

    def test_create_openai_client(self):
        from backend.services.llm_client import create_llm_client, LLMClient
        client = create_llm_client("openai_compatible", "test-key", "https://api.openai.com/v1")
        assert isinstance(client, LLMClient)

    def test_create_anthropic_client(self):
        from backend.services.llm_client import create_llm_client, AnthropicLLMClient
        client = create_llm_client("anthropic", "sk-ant-test")
        assert isinstance(client, AnthropicLLMClient)

    def test_create_gemini_client_is_openai_compatible(self):
        from backend.services.llm_client import create_llm_client, LLMClient
        client = create_llm_client(
            "openai_compatible", "gemini-key",
            "https://generativelanguage.googleapis.com/v1beta/openai/"
        )
        assert isinstance(client, LLMClient)

    def test_default_base_url_when_none(self):
        from backend.services.llm_client import create_llm_client, LLMClient
        client = create_llm_client("openai_compatible", "key", None)
        assert isinstance(client, LLMClient)


class TestLLMClientJsonParsing:
    """Test JSON parsing with multiple dynamic inputs."""

    @pytest.mark.parametrize("raw,expected_key", [
        ('{"score": 0.8, "reasoning": "good"}', "score"),
        ('```json\n{"score": 0.9}\n```', "score"),
        ('Some text {"result": "ok"} more text', "result"),
        ('```\n{"data": 1}\n```', "data"),
    ])
    def test_parse_json_variants(self, raw, expected_key):
        from backend.services.llm_client import LLMClient
        result = LLMClient._parse_json(raw)
        assert expected_key in result

    def test_parse_json_failure_returns_error(self):
        from backend.services.llm_client import LLMClient
        result = LLMClient._parse_json("not json at all")
        assert "error" in result
        assert "raw" in result


# ─── Provider Registry Tests ───────────────────────────────────────────────


class TestProviderRegistry:
    """Test ProviderRegistry with multiple dynamic settings contexts."""

    def test_list_providers_no_secrets(self, make_registry):
        """list_providers should NOT expose api_key."""
        registry = make_registry()
        providers = registry.list_providers()
        for p in providers:
            assert "api_key" not in p
            assert "id" in p
            assert "name" in p
            assert "configured" in p

    def test_get_client_configured_provider(self, make_registry):
        """get_client returns a client for a configured provider."""
        from backend.services.llm_client import LLMClient
        registry = make_registry()
        client = registry.get_client("openai")
        assert isinstance(client, LLMClient)

    def test_get_client_unconfigured_raises(self, make_registry):
        """get_client raises for unconfigured provider."""
        registry = make_registry()
        with pytest.raises(ValueError, match="not configured"):
            registry.get_client("anthropic")

    def test_get_client_unknown_raises(self, make_registry):
        """get_client raises for unknown provider ID."""
        registry = make_registry()
        with pytest.raises(ValueError, match="not configured"):
            registry.get_client("nonexistent")

    def test_get_client_anthropic(self, make_registry):
        """get_client returns AnthropicLLMClient for anthropic."""
        from backend.services.llm_client import AnthropicLLMClient
        registry = make_registry(ANTHROPIC_API_KEY="sk-ant-test")
        client = registry.get_client("anthropic")
        assert isinstance(client, AnthropicLLMClient)

    def test_get_defaults_openai(self, make_registry):
        """Defaults reflect OpenAI when legacy URL is OpenAI."""
        registry = make_registry(OPENAI_MODEL="gpt-4o", JUDGE_MODEL="gpt-4o-mini")
        defaults = registry.get_defaults()
        assert defaults["model_provider"] == "openai"
        assert defaults["model"] == "gpt-4o"
        assert defaults["judge_model"] == "gpt-4o-mini"
        assert defaults["judge_provider"] == "openai"

    def test_get_defaults_gemini(self, make_registry):
        """Defaults reflect Gemini when legacy URL is Gemini."""
        registry = make_registry(
            OPENAI_BASE_URL="https://generativelanguage.googleapis.com/v1beta/openai/",
            OPENAI_MODEL="gemini-2.0-flash",
        )
        defaults = registry.get_defaults()
        assert defaults["model_provider"] == "gemini"
        assert defaults["model"] == "gemini-2.0-flash"

    def test_anthropic_models_hardcoded(self, make_registry):
        """Anthropic models should be hardcoded list."""
        from backend.services.providers import ANTHROPIC_MODELS
        assert len(ANTHROPIC_MODELS) > 0
        assert any("claude" in m for m in ANTHROPIC_MODELS)

    def test_get_provider_returns_config(self, make_registry):
        registry = make_registry(ANTHROPIC_API_KEY="key")
        provider = registry.get_provider("anthropic")
        assert provider is not None
        assert provider.id == "anthropic"
        assert provider.configured is True

    def test_get_provider_unknown_returns_none(self, make_registry):
        registry = make_registry()
        assert registry.get_provider("nonexistent") is None


# ─── Schema Tests ───────────────────────────────────────────────────────────


class TestRunConfigSchema:
    """Test RunConfig with multiple dynamic config contexts."""

    @pytest.mark.parametrize("config_dict,expected_provider", [
        ({}, None),
        ({"model_provider": "gemini"}, "gemini"),
        ({"model_provider": "openai", "judge_provider": "anthropic"}, "openai"),
        ({"model_provider": "custom", "improver_provider": "gemini"}, "custom"),
    ])
    def test_provider_fields_optional(self, config_dict, expected_provider):
        from backend.schemas import RunConfig
        config = RunConfig(**config_dict)
        assert config.model_provider == expected_provider

    def test_full_multi_provider_config(self):
        """A config with different provider per stage."""
        from backend.schemas import RunConfig
        config = RunConfig(
            model="gemini-2.0-flash",
            model_provider="gemini",
            judge_model="claude-sonnet-4-5-20250929",
            judge_provider="anthropic",
            improver_model="gpt-4o",
            improver_provider="openai",
            max_iterations=5,
            target_score=0.85,
        )
        assert config.model_provider == "gemini"
        assert config.judge_provider == "anthropic"
        assert config.improver_provider == "openai"
        assert config.max_iterations == 5

    def test_backward_compatible_config(self):
        """Old config without provider fields still works."""
        from backend.schemas import RunConfig
        config = RunConfig(model="gpt-4o-mini", judge_model="gpt-4o-mini")
        assert config.model_provider is None
        assert config.judge_provider is None
        assert config.improver_provider is None

    def test_model_dump_includes_providers(self):
        from backend.schemas import RunConfig
        config = RunConfig(model_provider="gemini", judge_provider="anthropic")
        d = config.model_dump()
        assert d["model_provider"] == "gemini"
        assert d["judge_provider"] == "anthropic"
        assert d["improver_provider"] is None


# ─── Pipeline _resolve_client Tests ────────────────────────────────────────


class TestPipelineResolveClient:
    """Test _resolve_client with multi dynamic config + settings combos."""

    @pytest.fixture
    def make_settings(self):
        """Override shared make_settings with pipeline-specific defaults."""
        def _make(**overrides):
            from backend.config import Settings
            defaults = {
                "OPENAI_API_KEY": "legacy-key",
                "OPENAI_BASE_URL": "https://api.openai.com/v1",
                "OPENAI_MODEL": "gpt-4o-mini",
                "JUDGE_MODEL": "gpt-4o-mini",
                "IMPROVER_MODEL": "gpt-4o",
            }
            defaults.update(overrides)
            return Settings(**defaults)
        return _make

    def test_no_provider_uses_legacy(self, make_settings):
        """Config without provider fields falls back to legacy."""
        from backend.services.pipeline import _resolve_client
        from backend.services.llm_client import LLMClient
        settings = make_settings()
        config = {"model": "gpt-4o"}
        client, model = _resolve_client(settings, config, "test")
        assert isinstance(client, LLMClient)
        assert model == "gpt-4o"

    def test_explicit_provider_creates_specific_client(self, make_settings):
        """Config with anthropic provider creates AnthropicLLMClient."""
        from backend.services.pipeline import _resolve_client
        from backend.services.llm_client import AnthropicLLMClient
        settings = make_settings(ANTHROPIC_API_KEY="sk-ant-test")
        config = {"judge_model": "claude-sonnet-4-5-20250929", "judge_provider": "anthropic"}
        client, model = _resolve_client(settings, config, "judge")
        assert isinstance(client, AnthropicLLMClient)
        assert model == "claude-sonnet-4-5-20250929"

    def test_gemini_provider(self, make_settings):
        """Config with gemini provider creates OpenAI-compatible client with Gemini URL."""
        from backend.services.pipeline import _resolve_client
        from backend.services.llm_client import LLMClient
        settings = make_settings(GEMINI_API_KEY="gem-key")
        config = {"model": "gemini-2.0-flash", "model_provider": "gemini"}
        client, model = _resolve_client(settings, config, "test")
        assert isinstance(client, LLMClient)
        assert model == "gemini-2.0-flash"

    def test_different_providers_per_stage(self, make_settings):
        """Each stage resolves its own provider independently."""
        from backend.services.pipeline import _resolve_client
        from backend.services.llm_client import LLMClient, AnthropicLLMClient
        settings = make_settings(
            GEMINI_API_KEY="gem-key",
            ANTHROPIC_API_KEY="ant-key",
            OPENAI_PROVIDER_API_KEY="oai-key",
        )
        config = {
            "model": "gemini-2.0-flash", "model_provider": "gemini",
            "judge_model": "claude-sonnet-4-5-20250929", "judge_provider": "anthropic",
            "improver_model": "gpt-4o", "improver_provider": "openai",
        }
        test_client, test_model = _resolve_client(settings, config, "test")
        judge_client, judge_model = _resolve_client(settings, config, "judge")
        improver_client, improver_model = _resolve_client(settings, config, "improver")

        assert isinstance(test_client, LLMClient)
        assert test_model == "gemini-2.0-flash"
        assert isinstance(judge_client, AnthropicLLMClient)
        assert judge_model == "claude-sonnet-4-5-20250929"
        assert isinstance(improver_client, LLMClient)
        assert improver_model == "gpt-4o"

    def test_fallback_model_from_settings(self, make_settings):
        """Model defaults to settings when not in config."""
        from backend.services.pipeline import _resolve_client
        settings = make_settings(OPENAI_MODEL="gpt-4o-mini", JUDGE_MODEL="gpt-4o")
        config = {}
        _, test_model = _resolve_client(settings, config, "test")
        _, judge_model = _resolve_client(settings, config, "judge")
        _, improver_model = _resolve_client(settings, config, "improver")
        assert test_model == "gpt-4o-mini"
        assert judge_model == "gpt-4o"
        assert improver_model == "gpt-4o"

    def test_unconfigured_provider_falls_back(self, make_settings):
        """Provider specified but not configured -> falls back to legacy."""
        from backend.services.pipeline import _resolve_client
        from backend.services.llm_client import LLMClient
        settings = make_settings()  # No ANTHROPIC_API_KEY
        config = {"judge_model": "claude-sonnet-4-5-20250929", "judge_provider": "anthropic"}
        client, model = _resolve_client(settings, config, "judge")
        # Falls back to legacy LLMClient since anthropic is not configured
        assert isinstance(client, LLMClient)
        assert model == "claude-sonnet-4-5-20250929"


# ─── API Endpoint Tests ────────────────────────────────────────────────────


class TestProvidersAPI:
    """Test provider API endpoints with FastAPI TestClient."""

    def test_get_providers(self, app_client):
        """GET /api/providers returns providers and defaults."""
        r = app_client.get("/api/providers")
        assert r.status_code == 200
        data = r.json()
        assert "providers" in data
        assert "defaults" in data
        assert len(data["providers"]) == 4
        provider_ids = [p["id"] for p in data["providers"]]
        assert "gemini" in provider_ids
        assert "openai" in provider_ids
        assert "anthropic" in provider_ids
        assert "custom" in provider_ids

    def test_providers_have_required_fields(self, app_client):
        """Each provider has id, name, configured."""
        r = app_client.get("/api/providers")
        for p in r.json()["providers"]:
            assert "id" in p
            assert "name" in p
            assert "configured" in p
            assert "api_key" not in p  # No secrets exposed

    def test_defaults_have_all_stages(self, app_client):
        """Defaults cover model, judge, improver with providers."""
        r = app_client.get("/api/providers")
        defaults = r.json()["defaults"]
        for key in ["model", "model_provider", "judge_model", "judge_provider", "improver_model", "improver_provider"]:
            assert key in defaults

    def test_get_models_unknown_provider(self, app_client):
        """GET /api/providers/nonexistent/models returns error."""
        r = app_client.get("/api/providers/nonexistent/models")
        assert r.status_code == 200
        data = r.json()
        assert data["models"] == []
        assert "error" in data

    def test_get_models_unconfigured_provider(self, app_client):
        """GET /api/providers/anthropic/models when not configured."""
        r = app_client.get("/api/providers/anthropic/models")
        data = r.json()
        # Either returns empty with error or hardcoded list depending on config
        assert "models" in data

    def test_custom_models_endpoint(self, app_client):
        """POST /api/providers/custom/models with invalid URL returns error."""
        r = app_client.post("/api/providers/custom/models", json={
            "base_url": "https://invalid.example.com/v1",
            "api_key": "fake",
        })
        assert r.status_code == 200
        data = r.json()
        assert "models" in data
        # Should have error since URL is invalid
        assert data["models"] == [] or "error" in data


# ─── Integration: RunConfig round-trip ──────────────────────────────────────


class TestRunConfigRoundTrip:
    """Test that RunConfig with providers survives JSON serialization."""

    @pytest.mark.parametrize("config_input", [
        # Context 1: All providers different
        {
            "model": "gemini-2.0-flash", "model_provider": "gemini",
            "judge_model": "claude-sonnet-4-5-20250929", "judge_provider": "anthropic",
            "improver_model": "gpt-4o", "improver_provider": "openai",
        },
        # Context 2: Same provider for all
        {
            "model": "gpt-4o", "model_provider": "openai",
            "judge_model": "gpt-4o-mini", "judge_provider": "openai",
            "improver_model": "gpt-4o", "improver_provider": "openai",
        },
        # Context 3: No providers (backward compat)
        {"model": "gpt-4o-mini"},
        # Context 4: Mixed - some with provider, some without
        {
            "model": "gemini-2.0-flash", "model_provider": "gemini",
            "judge_model": "gpt-4o-mini",
        },
    ])
    def test_config_json_roundtrip(self, config_input):
        from backend.schemas import RunConfig
        config = RunConfig(**config_input)
        dumped = config.model_dump()
        serialized = json.dumps(dumped)
        restored = RunConfig(**json.loads(serialized))
        assert restored.model == config.model
        assert restored.model_provider == config.model_provider
        assert restored.judge_model == config.judge_model
        assert restored.judge_provider == config.judge_provider
        assert restored.improver_model == config.improver_model
        assert restored.improver_provider == config.improver_provider
