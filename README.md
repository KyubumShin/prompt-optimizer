# Auto Prompt Optimization Pipeline

A self-contained web application that automates the prompt engineering cycle: test prompts on datasets, use LLM judges to evaluate quality, summarize failure patterns, and iteratively improve prompts until convergence.

## Pipeline Flow

The system runs a 4-stage optimization loop that continues until the prompt reaches target quality or converges:

```
                    +------------------+
                    |   Upload CSV +   |
                    |  Initial Prompt  |
                    +--------+---------+
                             |
                    +--------v---------+
              +---->|  Stage 1: TEST   |
              |     | Run prompt on    |
              |     | all test cases   |
              |     +--------+---------+
              |              |
              |     +--------v---------+
              |     |  Stage 2: JUDGE  |
              |     | LLM scores each  |
              |     | (input, output,  |
              |     |  expected)       |
              |     +--------+---------+
              |              |
              |     +--------v---------+
              |     | Stage 3: SUMMARIZE|
              |     | Aggregate judge  |
              |     | reasoning, find  |
              |     | failure+success  |
              |     | patterns         |
              |     +--------+---------+
              |              |
              |     +--------v---------+
              |     | Stage 4: IMPROVE |
              |     | LLM generates    |
              |     | better prompt    |
              |     | (with judge      |
              |     |  reasoning)      |
              |     +--------+---------+
              |              |
              |    [Converged?]---Yes---> Done!
              |         |
              |        No
              +--------+
```

## Directory Structure

```
prompt-optimizer/
├── backend/
│   ├── main.py                    # FastAPI app, CORS, startup
│   ├── config.py                  # pydantic-settings (env vars)
│   ├── database.py                # SQLAlchemy async engine + session
│   ├── models.py                  # 4 tables: runs, iterations, test_results, logs
│   ├── schemas.py                 # Pydantic request/response models
│   ├── api/
│   │   ├── runs.py                # CRUD + stop + feedback endpoints
│   │   ├── stream.py              # SSE endpoint for live updates
│   │   └── providers.py           # Provider discovery + model listing
│   ├── services/
│   │   ├── llm_client.py          # BaseLLMClient ABC + OpenAI/Anthropic implementations with shared retry logic
│   │   ├── providers.py           # ProviderRegistry, model filtering
│   │   ├── csv_loader.py          # CSV parse + validate
│   │   ├── pipeline.py            # Main orchestrator loop
│   │   ├── event_manager.py       # SSE event queue manager
│   │   ├── tester.py              # Stage 1: run prompt on dataset
│   │   ├── judge.py               # Stage 2: LLM judge scoring
│   │   ├── summarizer.py          # Stage 3: aggregate reasoning
│   │   └── improver.py            # Stage 4: generate better prompt
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── App.tsx                # Routes
│   │   ├── types.ts               # TypeScript interfaces (incl. ModelsResponse)
│   │   ├── lib/api.ts             # Axios API client (incl. model discovery)
│   │   ├── hooks/
│   │   │   ├── useRuns.ts         # React Query hooks
│   │   │   └── useSSE.ts          # SSE hook for live updates
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx      # List all runs
│   │   │   ├── NewRun.tsx         # Create run form (3-step wizard, model dropdowns)
│   │   │   ├── RunDetail.tsx      # Run progress + results
│   │   │   └── IterationDetail.tsx # Per-iteration test results
│   │   └── components/
│   │       ├── AppShell.tsx       # Layout + navigation
│   │       ├── ScoreChart.tsx     # Line chart (Recharts)
│   │       ├── PromptDiff.tsx     # Side-by-side diff
│   │       ├── TestResultTable.tsx # Results with reasoning
│   │       ├── LogViewer.tsx      # Filterable log view
│   │       ├── RunCard.tsx        # Dashboard card
│   │       └── StatusBadge.tsx    # Status indicator
│   ├── package.json
│   ├── vite.config.ts
│   └── tsconfig.json
├── docs/
│   └── architecture.md            # Multi-provider architecture documentation
└── tests/
    ├── conftest.py                # Shared pytest fixtures
    ├── test_multi_provider.py     # 51 unit tests for multi-provider support
    ├── test_e2e.py                # End-to-end test suite
    ├── test_e2e_multi_column.py   # Multi-column CSV E2E tests
    ├── test_data.csv              # 10 example test cases
    ├── test_data_multi_column.csv # Multi-column test data
    └── test_data_ko.csv           # Korean language test data
```

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- An OpenAI API key (or compatible API endpoint)

### Setup

1. Clone or navigate to the project:
```bash
cd prompt-optimizer
```

2. Create a `.env` file in the project root:
```bash
cat > backend/.env << EOF
OPENAI_API_KEY=your_api_key_here
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
JUDGE_MODEL=gpt-4o-mini
IMPROVER_MODEL=gpt-4o
EOF
```

3. Install backend dependencies:
```bash
pip3 install -r backend/requirements.txt
```

4. Install frontend dependencies:
```bash
cd frontend
npm install
cd ..
```

5. Start the backend server:
```bash
python3 -m uvicorn backend.main:app --reload --port 8000
```

6. In a new terminal, start the frontend development server:
```bash
cd frontend
npm run dev
```

7. Open your browser and navigate to:
```
http://localhost:5173
```

## Configuration

The application is configured via environment variables. Create a `.env` file in the `backend/` directory with the following settings:

### Required Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | Your OpenAI API key (or compatible provider) | (required) |

### Optional Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_BASE_URL` | API endpoint URL (supports Google Gemini and other OpenAI-compatible APIs) | `https://api.openai.com/v1` |
| `OPENAI_MODEL` | Model for test stage | `gpt-4o-mini` |
| `JUDGE_MODEL` | Model for judge stage | `gpt-4o-mini` |
| `IMPROVER_MODEL` | Model for improve stage | `gpt-4o` |
| `GEMINI_API_KEY` | Google Gemini API key | (optional) |
| `GEMINI_BASE_URL` | Gemini API endpoint | `https://generativelanguage.googleapis.com/v1beta/openai/` |
| `ANTHROPIC_API_KEY` | Anthropic API key | (optional) |
| `OPENAI_PROVIDER_API_KEY` | Explicit OpenAI provider API key | (optional) |
| `OPENAI_PROVIDER_BASE_URL` | OpenAI provider endpoint | `https://api.openai.com/v1` |
| `CORS_ORIGINS` | Comma-separated allowed origins | `http://localhost:5173,http://localhost:3000` |
| `DATABASE_URL` | SQLAlchemy database URL | `sqlite+aiosqlite:///./prompt_optimizer.db` |
| `DEFAULT_CONCURRENCY` | Concurrent LLM requests | `5` |
| `DEFAULT_MAX_ITERATIONS` | Maximum optimization iterations | `10` |
| `DEFAULT_TARGET_SCORE` | Target quality score (0-1) | `0.9` |
| `DEFAULT_TEMPERATURE` | LLM temperature | `0.7` |
| `CONVERGENCE_THRESHOLD` | Score improvement threshold for stagnation detection | `0.02` |
| `CONVERGENCE_PATIENCE` | Consecutive rounds below threshold before stopping | `2` |

## Multi-Provider Support

The system supports using different LLM providers for each pipeline stage, allowing you to optimize for cost, performance, and quality at each step.

### Supported Providers

- **OpenAI** - GPT-4, GPT-4o, GPT-4o-mini, etc.
- **Google Gemini** - Gemini 1.5 Flash, Gemini 1.5 Pro, etc.
- **Anthropic** - Claude 3.5 Sonnet, Claude 3 Opus, etc.
- **Custom OpenAI-Compatible** - Any OpenAI-compatible endpoint (local models, Azure, etc.)

### Per-Stage Configuration

Each pipeline stage can use a different provider by specifying `model_provider`, `judge_provider`, and `improver_provider` in your run configuration:

```json
{
  "model": "gpt-4o-mini",
  "model_provider": "openai",
  "judge_model": "gemini-1.5-flash",
  "judge_provider": "gemini",
  "improver_model": "claude-3-5-sonnet-20241022",
  "improver_provider": "anthropic",
  "max_iterations": 10,
  "target_score": 0.9
}
```

### Example: Mixed Provider Setup

Use fast, cost-effective models for testing, and powerful models for judging and improving:

```json
{
  "model": "gemini-1.5-flash",
  "model_provider": "gemini",
  "judge_model": "gpt-4o",
  "judge_provider": "openai",
  "improver_model": "claude-3-5-sonnet-20241022",
  "improver_provider": "anthropic"
}
```

### Default Behavior

If you don't specify provider fields, the system uses `OPENAI_API_KEY` and `OPENAI_BASE_URL` for all stages.

## How to Use

### 1. Create a New Run

1. Click the "New Run" button on the dashboard
2. Follow the 3-step wizard:
   - **Step 1**: Upload CSV - Upload your test dataset
   - **Step 2**: Write Prompt - Write initial prompt with column placeholders
   - **Step 3**: Configure - Select models from dropdown, adjust settings

### 2. Upload CSV Dataset

Your CSV must have:
- One or more input columns
- One expected output column (selected in the wizard)

### 3. Write Initial Prompt

Create a prompt template using placeholders for column names:
```
Translate the following text to French: {text}
```

Available placeholders are any column names from your CSV (except the expected output column).

### 4. Configure Settings

- **Model Selection**: Select models from auto-populated dropdowns (Test Model, Judge Model, Improver Model). Available models are fetched from your configured API provider. The default option shows the server-configured model name.
- **Custom URL**: Toggle "Use Custom OpenAI-Compatible URL" to fetch models from a different provider (e.g., switch from Gemini to OpenAI or a local endpoint). Enter the base URL and optionally an API key, then click "Fetch Models".
- **Max Iterations**: Maximum optimization rounds (default: 10)
- **Target Score**: Stop when average score reaches this threshold (0-1, default: 0.9)
- **Concurrency**: Number of parallel LLM requests (default: 5)
- **Temperature**: LLM temperature setting (default: 0.7)
- **Custom Judge Prompt**: Optional custom scoring criteria

### 5. Monitor Progress

Once started, you'll be redirected to the Run Detail page showing:
- Live progress updates via Server-Sent Events
- Current stage and iteration
- Score chart showing improvement over iterations
- Prompt comparison between iterations
- Test results with judge reasoning
- Detailed logs

### 6. Review Results

When the run completes (converged or max iterations reached):
- View the final optimized prompt
- Compare prompts across all iterations
- Examine individual test case results and judge reasoning
- View the full improver prompt (collapsible "Improver Prompt (Step 4)" section on each iteration detail page)
- Review the complete optimization log
- Copy the best prompt for use in production

## CSV Format

The CSV file must include:
- At least one input column
- One expected output column (you'll select which one during setup)

### Example

```csv
text,expected_output
"Hello, how are you?","Bonjour, comment allez-vous ?"
"Good morning","Bonjour"
"Thank you very much","Merci beaucoup"
```

In this example:
- `text` is the input column (referenced as `{text}` in your prompt)
- `expected_output` is what the judge will compare against

### Multi-Column Input

You can have multiple input columns:

```csv
source_lang,target_lang,text,expected_output
"en","fr","Hello","Bonjour"
"en","es","Hello","Hola"
```

Prompt example: `Translate from {source_lang} to {target_lang}: {text}`

## API Reference

### Provider Management

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/providers` | List all providers with config status and defaults |
| `GET` | `/api/providers/{id}/models` | Fetch available models for a provider |
| `POST` | `/api/providers/custom/models` | Fetch models from custom endpoint |

### Model Discovery

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/runs/models` | List available chat-completion models from configured provider |
| `POST` | `/api/runs/models/custom` | List models from a custom OpenAI-compatible URL |

### Run Management

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/runs` | Create new optimization run (multipart form) |
| `GET` | `/api/runs` | List all runs (ordered by creation date) |
| `GET` | `/api/runs/{id}` | Get run details with iterations |
| `DELETE` | `/api/runs/{id}` | Delete run and all related data |
| `POST` | `/api/runs/{id}/stop` | Stop a running optimization |
| `POST` | `/api/runs/{id}/feedback` | Submit human feedback for running pipeline |

### Iteration Data

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/runs/{id}/iterations` | List all iterations for a run |
| `GET` | `/api/runs/{id}/iterations/{num}` | Get iteration details with test results |

### Logs and Events

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/runs/{id}/logs` | Get logs (filterable by stage and level) |
| `GET` | `/api/runs/{id}/stream` | Server-Sent Events stream for live updates |

### Request Format: Create Run

```bash
curl -X POST http://localhost:8000/api/runs \
  -F "file=@test_data.csv" \
  -F "name=My Translation Test" \
  -F "initial_prompt=Translate to French: {text}" \
  -F "expected_column=expected_output" \
  -F 'config_json={"model":"gpt-4o-mini","max_iterations":10,"target_score":0.9}'
```

### SSE Event Types

The `/api/runs/{id}/stream` endpoint emits these events:

- `stage_start` - A pipeline stage begins (test, judge, summarize, improve)
- `test_progress` - Test stage progress update
- `iteration_complete` - Iteration finished with scores
- `feedback_requested` - Pipeline is waiting for human feedback
- `converged` - Pipeline converged (target reached or stagnation)
- `completed` - Pipeline completed (max iterations reached)
- `stopped` - Pipeline stopped by user
- `failed` - Pipeline encountered an error

## Tech Stack

### Backend
- **FastAPI** - Modern async web framework
- **SQLAlchemy 2.0** - Async ORM with relationship loading
- **SQLite** - Embedded database with async support (aiosqlite)
- **OpenAI Python SDK** - Multi-provider LLM client with streaming support
- **Anthropic Python SDK** - Native Claude API client
- **Pydantic** - Data validation and settings management

### Frontend
- **React 18** - UI framework with concurrent features
- **TypeScript** - Type-safe development
- **Vite** - Fast build tool and dev server
- **TailwindCSS** - Utility-first styling
- **React Query** - Server state management with caching
- **React Router** - Client-side routing
- **Recharts** - Declarative chart library
- **Axios** - HTTP client

### Real-time Communication
- **Server-Sent Events (SSE)** - Live progress updates from server to client

## Running Tests

The project includes comprehensive unit tests and end-to-end test suites.

### Unit Tests

Run the multi-provider unit tests (51 tests, no server required):

```bash
python3 -m pytest tests/test_multi_provider.py -v
```

These tests cover:
- Provider registry and configuration
- LLM client implementations (OpenAI, Anthropic, Gemini)
- Model filtering and validation
- API key handling and fallback logic
- Error handling and retry mechanisms

### End-to-End Tests

Ensure the backend server is running:
```bash
python3 -m uvicorn backend.main:app --reload --port 8000
```

Run the E2E test suites:

```bash
# Single-column CSV tests
python3 tests/test_e2e.py

# Multi-column CSV tests
python3 tests/test_e2e_multi_column.py
```

The E2E test suite includes:
- Creating a run with CSV upload
- Monitoring pipeline progress
- Validating iteration scores
- Checking prompt improvements
- Verifying convergence behavior
- Testing stop functionality
- Validating data cleanup
- Multi-column input handling

## Convergence Criteria

The pipeline stops optimization when any of these conditions are met:

### 1. Target Score Reached
- Average score across all test cases reaches or exceeds the configured target score
- Default target: 0.9 (90% quality)
- Configurable per run

### 2. Score Stagnation
- Score improvement falls below the convergence threshold for multiple consecutive iterations
- Default threshold: 0.02 (2% improvement)
- Default patience: 2 consecutive rounds
- Both values are configurable

### 3. Maximum Iterations Reached
- Pipeline completes the configured maximum number of iterations
- Default: 10 iterations
- Configurable per run

### Convergence Detection Example

```
Iteration 1: avg_score = 0.65
Iteration 2: avg_score = 0.78 (improvement: 0.13)
Iteration 3: avg_score = 0.85 (improvement: 0.07)
Iteration 4: avg_score = 0.86 (improvement: 0.01) <- below threshold
Iteration 5: avg_score = 0.865 (improvement: 0.005) <- below threshold
→ Converged due to stagnation (2 consecutive rounds below 0.02)
```

## Project Features

### Live Progress Tracking
- Real-time updates via Server-Sent Events
- Progress bars for test execution
- Stage indicators showing current pipeline phase

### Detailed Analytics
- Score charts showing improvement trends
- Per-iteration comparison
- Test-level results with judge reasoning
- Filterable logs by stage and level

### Prompt Engineering Insights
- Side-by-side prompt comparison
- Improvement reasoning from LLM
- Failure pattern summaries
- Success pattern analysis (what's working well)
- Judge feedback for each test case
- Full improver prompt visibility (see exactly what the LLM received in Step 4)

### Human Feedback Integration
- Enable `human_feedback_enabled` in run configuration
- Pipeline pauses after each iteration's summarize stage
- User can provide written feedback that the improver incorporates into the next iteration
- Automatic continuation after 30-minute timeout if no feedback provided
- Interactive feedback UI in the Run Detail page

### Flexible Configuration
- Custom judge prompts for domain-specific scoring
- Adjustable convergence criteria
- Model selection per pipeline stage
- Multi-provider support with per-stage configuration
- Concurrency control for cost/speed tradeoff

## Troubleshooting

### Backend won't start
- Check that port 8000 is not in use
- Verify `.env` file exists with `OPENAI_API_KEY`
- Ensure all dependencies are installed: `pip3 install -r backend/requirements.txt`

### Frontend won't start
- Check that port 5173 is not in use
- Verify Node.js version is 18+
- Delete `node_modules` and reinstall: `rm -rf node_modules && npm install`

### CSV upload fails
- Ensure CSV has at least 2 columns (1 input + 1 expected output)
- Check that column names don't have special characters
- Verify file encoding is UTF-8

### Pipeline fails immediately
- Check API key is valid and has credits
- Verify `OPENAI_BASE_URL` matches your provider
- Review logs in the Run Detail page for specific error messages

### No live updates
- Ensure browser supports Server-Sent Events (all modern browsers do)
- Check browser console for connection errors
- Verify backend is running and accessible

## License

This project is provided as-is for educational and commercial use.

## Support

For issues, questions, or contributions, please refer to the project repository or contact the development team.
