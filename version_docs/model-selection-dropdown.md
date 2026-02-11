# Model Selection Dropdown with Provider Auto-Detection

**Date**: 2026-02-11
**Commit**: `4f787d8`

## Summary

Replaced free-form text inputs for model selection with select dropdowns that auto-populate from the configured API provider. Added support for switching to a custom OpenAI-compatible URL with manual model entry.

## Problem

- Users had to manually type exact model IDs (e.g., `gemini-2.0-flash`) into text fields
- Hardcoded `gpt-4o` defaults were sent to Gemini backends, causing errors
- No way to discover which models were available from the configured provider

## Solution

### Backend: Two new API endpoints

**`GET /api/runs/models`**
- Fetches available models from the configured provider using `AsyncOpenAI.models.list()`
- Filters to chat-completion models (excludes embedding, TTS, whisper, DALL-E, moderation)
- Returns model list, base URL, and server defaults from `.env`
- Graceful error handling returns `{ models: [], error: "..." }` on failure

**`POST /api/runs/models/custom`**
- Accepts `{ base_url, api_key? }` to fetch models from any OpenAI-compatible endpoint
- Falls back to server API key if none provided
- Same filtering logic as the default endpoint

### Frontend: Dropdown UI with custom URL toggle

- Three `<select>` dropdowns replace `<input type="text">` for Test Model, Judge Model, and Improver Model
- Models auto-fetched when Step 3 becomes visible
- Default option shows "Server default (model-name)" using server-provided defaults
- "Use Custom OpenAI-Compatible URL" checkbox toggles custom provider mode
- Custom mode: input fields for Base URL and optional API Key with a "Fetch Models" button
- Toggling off reverts to default provider models

## Files Changed

| File | Lines | Change |
|------|-------|--------|
| `backend/api/runs.py` | +71 | Added `/models` and `/models/custom` endpoints, `_is_chat_model()` helper, `CustomModelsRequest` schema |
| `frontend/src/types.ts` | +12 | Added `ModelsResponse` and `CustomModelsResponse` interfaces |
| `frontend/src/lib/api.ts` | +10 | Added `fetchModels()` and `fetchCustomModels()` API client methods |
| `frontend/src/pages/NewRun.tsx` | +130/-6 | Replaced text inputs with select dropdowns, added custom URL toggle UI, model fetch logic |

**Total**: 4 files changed, 223 insertions, 8 deletions

## API Reference

### GET /api/runs/models

Response:
```json
{
  "models": ["gemini-2.0-flash", "gemini-2.0-pro", ...],
  "base_url": "https://generativelanguage.googleapis.com/v1beta",
  "defaults": {
    "model": "gemini-2.0-flash",
    "judge_model": "gemini-2.0-flash",
    "improver_model": "gemini-2.0-pro"
  }
}
```

### POST /api/runs/models/custom

Request:
```json
{
  "base_url": "https://api.openai.com/v1",
  "api_key": "sk-..."
}
```

Response:
```json
{
  "models": ["gpt-4o", "gpt-4o-mini", "o1-preview", ...]
}
```

## Model Filtering

The `_is_chat_model()` helper excludes models containing these keywords (case-insensitive):
- `embed` (embedding models)
- `tts` (text-to-speech)
- `whisper` (speech-to-text)
- `dall-e` (image generation)
- `moderation` (content moderation)
