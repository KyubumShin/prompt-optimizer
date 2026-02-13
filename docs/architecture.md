# Architecture

## System Overview
- Prompt Optimizer is a web application that automates prompt engineering through iterative optimization
- 4-stage pipeline: Test → Judge → Summarize → Improve, looping until convergence
- FastAPI async backend + React TypeScript frontend + SQLite database
- Real-time progress via Server-Sent Events (SSE)

## Architecture Diagram
```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (React)                       │
│  Dashboard │ NewRun Wizard │ RunDetail │ IterationDetail  │
│                        │                                  │
│              useSSE ◄──┤──► useRuns (React Query)        │
└────────────────────────┼──────────────────────────────────┘
                         │ HTTP + SSE
┌────────────────────────┼──────────────────────────────────┐
│                    FastAPI Backend                         │
│                        │                                  │
│  ┌─────────┐  ┌───────┴───────┐  ┌──────────────┐       │
│  │ /api/   │  │  /api/runs/   │  │ /api/runs/   │       │
│  │providers│  │  CRUD+stop+   │  │ {id}/stream   │       │
│  │         │  │  feedback      │  │ (SSE)        │       │
│  └────┬────┘  └───────┬───────┘  └──────┬───────┘       │
│       │               │                  │                │
│  ┌────┴────┐  ┌───────┴───────┐  ┌──────┴───────┐       │
│  │Provider │  │   Pipeline    │  │   Event      │       │
│  │Registry │  │  Orchestrator │  │   Manager    │       │
│  └────┬────┘  └───┬───┬───┬──┘  └──────────────┘       │
│       │           │   │   │                               │
│  ┌────┴────┐  ┌───┴┐ ┌┴──┐ ┌┴────────┐                  │
│  │  LLM    │  │Test│ │Jdg│ │Summarize│ │Improve│        │
│  │ Client  │  │ er │ │ e │ │  r      │ │  r    │        │
│  │ Factory │  └────┘ └───┘ └─────────┘ └───────┘        │
│  └────┬────┘                                              │
│       │                                                   │
│  ┌────┴─────────────────┐                                 │
│  │    BaseLLMClient     │ (ABC)                           │
│  ├──────────┬───────────┤                                 │
│  │LLMClient │Anthropic  │                                 │
│  │(OpenAI)  │LLMClient  │                                 │
│  └──────────┴───────────┘                                 │
└───────────────────────────────────────────────────────────┘
                         │
                  ┌──────┴──────┐
                  │   SQLite    │
                  │ (aiosqlite) │
                  └─────────────┘
```

## Design Decisions

### 1. Multi-Provider Architecture
**Decision**: Support multiple LLM providers (OpenAI, Gemini, Anthropic) with per-stage provider selection.

**Reasoning**:
- Different models excel at different tasks. A fast/cheap model (Gemini Flash) can run test cases while an expensive/capable model (GPT-4o) can generate improvements.
- Users shouldn't be locked into a single provider.
- Cost optimization: use cheap models for high-volume test stage, expensive models only for improvement.

**Implementation**:
- `BaseLLMClient` ABC defines the interface (`complete`, `complete_json`)
- `LLMClient` handles all OpenAI-compatible APIs (OpenAI, Gemini, custom endpoints)
- `AnthropicLLMClient` uses the native Anthropic SDK (different API format)
- `create_llm_client()` factory dispatches by `provider_type`
- `ProviderRegistry` manages provider discovery, model listing, and client creation
- Pipeline's `_resolve_client()` maps stage → provider → client at runtime

**Trade-offs**:
- Added complexity vs. single-client approach
- Anthropic requires separate SDK (not OpenAI-compatible)
- Legacy backward compatibility maintained via fallback logic in `_resolve_client()`

### 2. Async Pipeline with SSE
**Decision**: Run the pipeline as an asyncio background task with Server-Sent Events for progress.

**Reasoning**:
- Pipeline runs can take minutes to hours. HTTP request-response won't work.
- SSE is simpler than WebSockets for unidirectional server-to-client updates.
- asyncio tasks allow concurrent test case execution within each iteration.

**Implementation**:
- `asyncio.create_task()` launches the pipeline in `create_run` endpoint
- `EventManager` maintains per-run subscriber queues (multi-subscriber support)
- `add_done_callback` on pipeline tasks catches unhandled exceptions
- Semaphore-based concurrency control in tester.py

**Trade-offs**:
- In-memory event queues don't survive server restart (acceptable for development/small scale)
- SSE doesn't support binary data or bidirectional communication
- Pipeline state is DB-backed, so runs can be inspected even if SSE disconnects

### 3. LLM-as-Judge Pattern
**Decision**: Use a separate LLM call to score each test result rather than exact string matching.

**Reasoning**:
- Natural language outputs rarely match exactly. "Bonjour" vs "Salut" are both valid French greetings.
- LLM judges can evaluate semantic correctness, tone, completeness.
- Custom judge prompts allow domain-specific evaluation criteria.

**Implementation**:
- Judge receives: input data, expected output, actual output, and scoring prompt
- Returns JSON with `score` (0-1) and `reasoning`
- Custom judge prompts override the default scoring criteria
- Concurrent judging with semaphore-controlled parallelism

### 4. Convergence Detection
**Decision**: Three-way convergence: target score, stagnation detection, and max iterations.

**Reasoning**:
- Target score alone might never be reached for hard problems.
- Without stagnation detection, the pipeline wastes API calls when improvements plateau.
- Max iterations provides a hard ceiling for cost control.

**Implementation**:
- `CONVERGENCE_THRESHOLD` (default 0.02) and `CONVERGENCE_PATIENCE` (default 2) control stagnation
- Score history tracked in `prev_scores` list
- Stagnation = consecutive rounds where `abs(score[i] - score[i-1]) < threshold`

### 5. Configuration Strategy
**Decision**: Pydantic Settings with env vars + backward-compatible legacy detection.

**Reasoning**:
- The system started with a single `OPENAI_API_KEY` + `OPENAI_BASE_URL` pointing to any provider.
- Multi-provider support was added later. Old `.env` files must keep working.
- Legacy detection: if `OPENAI_BASE_URL` contains "generativelanguage.googleapis.com", it's Gemini.

**Implementation**:
- `Settings._is_legacy_gemini()` detects legacy Gemini config
- `Settings.get_providers()` builds the provider list with fallback logic
- Explicit keys (`GEMINI_API_KEY`, `ANTHROPIC_API_KEY`) override legacy auto-detection
- `CORS_ORIGINS` env var allows deployment-specific CORS configuration

### 6. Human Feedback Loop
**Decision**: Optional human-in-the-loop feedback between iterations.

**Reasoning**:
- Automated optimization may miss domain nuances that humans can catch.
- Feedback can steer improvements in directions the LLM wouldn't discover alone.
- Making it optional keeps the default fully-automated flow simple.

**Implementation**:
- `human_feedback_enabled` flag in RunConfig
- Pipeline emits `feedback_requested` SSE event and blocks on `asyncio.Event`
- User feedback injected into the summary dict before the improve stage
- 30-minute timeout (`FEEDBACK_TIMEOUT_SECONDS`) prevents indefinite blocking

## Database Schema

```
runs (1) ──── (*) iterations (1) ──── (*) test_results
  │
  └──── (*) logs
```

- **runs**: Optimization run metadata (prompt, config, status, best result)
- **iterations**: Per-iteration data (prompt version, scores, summary, improvement reasoning)
- **test_results**: Per-test-case results (input, expected, actual, score, judge reasoning)
- **logs**: Structured pipeline logs (stage, level, message, optional JSON data)

All relationships use cascade delete. SQLAlchemy 2.0 Mapped types with async session.

## Request Flow

### Create Run
1. Client POSTs multipart form (CSV + prompt + config)
2. Server parses CSV, validates columns, creates Run record
3. Pipeline launched as `asyncio.create_task()`
4. Client receives Run response immediately

### Pipeline Execution
1. For each iteration:
   a. **Test**: Run prompt on all test cases (concurrent with semaphore)
   b. **Judge**: Score each result (concurrent)
   c. **Summarize**: Aggregate scores, identify failure patterns
   d. **(Optional) Human Feedback**: Emit SSE event, wait for input
   e. **Check convergence**: Target reached? Stagnated? Max iterations?
   f. **Improve**: LLM generates new prompt based on summary
2. Each stage emits SSE events for progress tracking
3. Results persisted to DB after each iteration

### SSE Stream
1. Client GETs `/api/runs/{id}/stream`
2. EventManager creates subscriber queue for this run
3. Pipeline pushes events to all subscribers
4. Terminal events (completed/converged/failed/stopped) end the stream
5. 30-second keepalive comments prevent connection timeouts

## Error Handling

- **Pipeline errors**: Caught at top level, run status set to "failed", error logged
- **LLM API errors**: Exponential backoff retry (2s → 4s → 8s → 16s → 32s), max 5 attempts
- **Task tracking**: `add_done_callback` on pipeline tasks logs unhandled exceptions
- **Unconfigured providers**: Falls back to legacy single-provider config
- **JSON parse errors**: Regex fallback to extract JSON from markdown code blocks

## Testing Strategy

- **Unit tests** (`test_multi_provider.py`, 51 tests): Config, providers, clients, pipeline routing, schemas, API endpoints
- **Shared fixtures** (`conftest.py`): `make_settings`, `make_registry`, `app_client` factories
- **E2E tests** (`test_e2e.py`, `test_e2e_multi_column.py`): Full pipeline with running server
- No mocking of database (uses real SQLite), mocking only for external LLM calls where needed
