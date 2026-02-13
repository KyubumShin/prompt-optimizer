# Auto Prompt Optimization Pipeline

프롬프트 엔지니어링 사이클을 자동화하는 독립형 웹 애플리케이션입니다. 데이터셋에서 프롬프트를 테스트하고, LLM 심사자를 사용하여 품질을 평가하며, 실패 패턴을 요약하고, 수렴할 때까지 반복적으로 프롬프트를 개선합니다.

## 파이프라인 흐름

시스템은 프롬프트가 목표 품질에 도달하거나 수렴할 때까지 계속되는 4단계 최적화 루프를 실행합니다:

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
              |     | failure patterns |
              |     +--------+---------+
              |              |
              |     +--------v---------+
              |     | Stage 4: IMPROVE |
              |     | LLM generates    |
              |     | better prompt    |
              |     +--------+---------+
              |              |
              |    [Converged?]---Yes---> Done!
              |         |
              |        No
              +--------+
```

## 디렉토리 구조

```
prompt-optimizer/
├── backend/
│   ├── main.py                    # FastAPI app, CORS, startup
│   ├── config.py                  # pydantic-settings (env vars)
│   ├── database.py                # SQLAlchemy async engine + session
│   ├── models.py                  # 4 tables: runs, iterations, test_results, logs
│   ├── schemas.py                 # Pydantic request/response models
│   ├── api/
│   │   ├── runs.py                # CRUD + 중지 + 피드백 엔드포인트
│   │   ├── stream.py              # SSE endpoint for live updates
│   │   └── providers.py           # 프로바이더 디스커버리 + 모델 목록
│   ├── services/
│   │   ├── llm_client.py          # BaseLLMClient ABC + OpenAI/Anthropic 구현체 (공유 재시도 로직)
│   │   ├── providers.py           # ProviderRegistry, 모델 필터링
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
│   │   ├── types.ts               # TypeScript interfaces
│   │   ├── lib/api.ts             # Axios API client
│   │   ├── hooks/
│   │   │   ├── useRuns.ts         # React Query hooks
│   │   │   └── useSSE.ts          # SSE hook for live updates
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx      # List all runs
│   │   │   ├── NewRun.tsx         # Create run form (3-step wizard)
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
│   └── architecture.md            # 아키텍처 문서
└── tests/
    ├── conftest.py                # 공유 픽스처
    ├── test_multi_provider.py     # 51개 유닛 테스트
    ├── test_e2e.py                # End-to-end test suite
    ├── test_e2e_multi_column.py   # 다중 컬럼 E2E 테스트
    ├── test_data.csv              # 10 example test cases
    ├── test_data_multi_column.csv # 다중 컬럼 예제
    └── test_data_ko.csv           # 한국어 예제
```

## 빠른 시작

### 사전 요구 사항

- Python 3.10+
- Node.js 18+
- OpenAI API 키 (또는 호환되는 API 엔드포인트)

### 설정

1. 프로젝트를 클론하거나 이동합니다:
```bash
cd prompt-optimizer
```

2. 프로젝트 루트에 `.env` 파일을 생성합니다:
```bash
cat > backend/.env << EOF
OPENAI_API_KEY=your_api_key_here
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
JUDGE_MODEL=gpt-4o-mini
IMPROVER_MODEL=gpt-4o
EOF
```

3. 백엔드 의존성을 설치합니다:
```bash
pip3 install -r backend/requirements.txt
```

4. 프론트엔드 의존성을 설치합니다:
```bash
cd frontend
npm install
cd ..
```

5. 백엔드 서버를 시작합니다:
```bash
python3 -m uvicorn backend.main:app --reload --port 8000
```

6. 새 터미널에서 프론트엔드 개발 서버를 시작합니다:
```bash
cd frontend
npm run dev
```

7. 브라우저를 열고 다음 주소로 이동합니다:
```
http://localhost:5173
```

## 구성

애플리케이션은 환경 변수를 통해 구성됩니다. `backend/` 디렉토리에 다음 설정으로 `.env` 파일을 생성하세요:

### 필수 설정

| 변수 | 설명 | 기본값 |
|------|------|--------|
| `OPENAI_API_KEY` | OpenAI API 키 (또는 호환 가능한 제공업체) | (필수) |

### 선택적 설정

| 변수 | 설명 | 기본값 |
|------|------|--------|
| `OPENAI_BASE_URL` | API 엔드포인트 URL (Google Gemini 및 기타 OpenAI 호환 API 지원) | `https://api.openai.com/v1` |
| `OPENAI_MODEL` | 테스트 단계용 모델 | `gpt-4o-mini` |
| `JUDGE_MODEL` | 심사 단계용 모델 | `gpt-4o-mini` |
| `IMPROVER_MODEL` | 개선 단계용 모델 | `gpt-4o` |
| `GEMINI_API_KEY` | Google Gemini API 키 (선택, 레거시 설정에서 자동 감지) | - |
| `GEMINI_BASE_URL` | Gemini API 엔드포인트 | `https://generativelanguage.googleapis.com/v1beta/openai/` |
| `ANTHROPIC_API_KEY` | Anthropic API 키 (선택) | - |
| `OPENAI_PROVIDER_API_KEY` | 레거시가 Gemini를 가리킬 때 명시적 OpenAI 키 (선택) | - |
| `OPENAI_PROVIDER_BASE_URL` | OpenAI 프로바이더 엔드포인트 | `https://api.openai.com/v1` |
| `CORS_ORIGINS` | 쉼표로 구분된 허용 오리진 | `http://localhost:5173,http://localhost:3000` |
| `DATABASE_URL` | SQLAlchemy 데이터베이스 URL | `sqlite+aiosqlite:///./prompt_optimizer.db` |
| `DEFAULT_CONCURRENCY` | 동시 LLM 요청 수 | `5` |
| `DEFAULT_MAX_ITERATIONS` | 최대 최적화 반복 횟수 | `10` |
| `DEFAULT_TARGET_SCORE` | 목표 품질 점수 (0-1) | `0.9` |
| `DEFAULT_TEMPERATURE` | LLM 온도 | `0.7` |
| `CONVERGENCE_THRESHOLD` | 정체 감지를 위한 점수 개선 임계값 | `0.02` |
| `CONVERGENCE_PATIENCE` | 중지 전 임계값 미만의 연속 라운드 수 | `2` |

### 대체 LLM 제공업체 사용 (레거시)

애플리케이션은 OpenAI 호환 API를 지원합니다. 예를 들어, Google Gemini를 사용하려면:

```bash
OPENAI_API_KEY=your_google_api_key
OPENAI_BASE_URL=https://generativelanguage.googleapis.com/v1beta
OPENAI_MODEL=gemini-1.5-flash
JUDGE_MODEL=gemini-1.5-flash
IMPROVER_MODEL=gemini-1.5-pro
```

### 멀티 프로바이더 지원

v2.0부터 파이프라인의 각 단계(테스트, 심사, 개선)가 서로 다른 LLM 프로바이더를 사용할 수 있습니다. 이를 통해 각 작업에 가장 적합한 모델을 선택할 수 있습니다.

#### 지원 프로바이더

- **OpenAI** - GPT-4, GPT-4o, GPT-3.5 등
- **Google Gemini** - Gemini 1.5 Pro, Flash 등
- **Anthropic** - Claude 3.5 Sonnet, Opus, Haiku
- **사용자 정의 엔드포인트** - OpenAI 호환 API

#### 프로바이더별 구성

각 파이프라인 단계는 독립적으로 프로바이더를 지정할 수 있습니다:

```bash
# OpenAI 프로바이더
OPENAI_PROVIDER_API_KEY=sk-...
OPENAI_PROVIDER_BASE_URL=https://api.openai.com/v1

# Gemini 프로바이더
GEMINI_API_KEY=AIza...
GEMINI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/

# Anthropic 프로바이더
ANTHROPIC_API_KEY=sk-ant-...
```

#### 단계별 프로바이더 선택

실행 생성 시 각 단계에 대해 프로바이더와 모델을 지정할 수 있습니다:

```json
{
  "model": "gpt-4o-mini",
  "model_provider": "openai",
  "judge_model": "claude-3-5-sonnet-20241022",
  "judge_provider": "anthropic",
  "improver_model": "gemini-1.5-pro",
  "improver_provider": "gemini"
}
```

#### 프로바이더 예시

**시나리오 1: 비용 최적화**
- 테스트: `gpt-4o-mini` (OpenAI) - 빠르고 저렴
- 심사: `gemini-1.5-flash` (Gemini) - 빠른 평가
- 개선: `claude-3-5-sonnet` (Anthropic) - 고품질 개선

**시나리오 2: 품질 우선**
- 테스트: `gpt-4o` (OpenAI)
- 심사: `claude-3-5-sonnet` (Anthropic)
- 개선: `gemini-1.5-pro` (Gemini)

**시나리오 3: 단일 프로바이더**
- 모든 단계: `gpt-4o-mini` (OpenAI)

#### 하위 호환성

기존 단일 프로바이더 설정은 계속 작동합니다. `model_provider` 필드가 지정되지 않으면 시스템은 레거시 `OPENAI_API_KEY` 및 `OPENAI_BASE_URL` 설정을 사용합니다.

## 사용 방법

### 1. 새 실행 생성

1. 대시보드에서 "New Run" 버튼을 클릭합니다
2. 3단계 마법사를 따릅니다:
   - **1단계**: Upload CSV - 테스트 데이터셋을 업로드합니다
   - **2단계**: Configure - 예상 출력 컬럼을 선택하고 초기 프롬프트를 작성합니다
   - **3단계**: Settings - 모델, 반복 횟수, 목표 점수를 구성합니다

### 2. CSV 데이터셋 업로드

CSV에는 다음이 포함되어야 합니다:
- 하나 이상의 입력 컬럼
- 하나의 예상 출력 컬럼 (마법사에서 선택)

### 3. 초기 프롬프트 작성

컬럼 이름의 플레이스홀더를 사용하여 프롬프트 템플릿을 생성합니다:
```
Translate the following text to French: {text}
```

사용 가능한 플레이스홀더는 CSV의 모든 컬럼 이름입니다 (예상 출력 컬럼 제외).

### 4. 설정 구성

- **모델 선택**: 테스트, 심사, 개선을 위한 모델을 선택합니다
- **프로바이더 선택**: 각 단계에 대해 LLM 프로바이더를 선택합니다 (OpenAI, Gemini, Anthropic)
- **최대 반복 횟수**: 최대 최적화 라운드 수 (기본값: 10)
- **목표 점수**: 평균 점수가 이 임계값에 도달하면 중지 (0-1, 기본값: 0.9)
- **동시성**: 병렬 LLM 요청 수 (기본값: 5)
- **온도**: LLM 온도 설정 (기본값: 0.7)
- **사용자 지정 심사 프롬프트**: 선택적 사용자 지정 채점 기준
- **휴먼 피드백**: 각 반복 후 수동 피드백 활성화 (선택적)

### 5. 진행 상황 모니터링

시작하면 실행 세부 정보 페이지로 리디렉션되어 다음을 표시합니다:
- Server-Sent Events를 통한 실시간 진행 업데이트
- 현재 단계 및 반복
- 반복에 따른 개선을 보여주는 점수 차트
- 반복 간 프롬프트 비교
- 심사자 추론이 포함된 테스트 결과
- 상세 로그
- 휴먼 피드백 요청 (활성화된 경우)

### 6. 결과 검토

실행이 완료되면 (수렴 또는 최대 반복 도달):
- 최종 최적화된 프롬프트 보기
- 모든 반복에서 프롬프트 비교
- 개별 테스트 케이스 결과 및 심사자 추론 검토
- 전체 최적화 로그 검토
- 프로덕션에서 사용하기 위해 최상의 프롬프트 복사

## CSV 형식

CSV 파일에는 다음이 포함되어야 합니다:
- 최소 하나의 입력 컬럼
- 하나의 예상 출력 컬럼 (설정 중에 선택)

### 예제

```csv
text,expected_output
"Hello, how are you?","Bonjour, comment allez-vous ?"
"Good morning","Bonjour"
"Thank you very much","Merci beaucoup"
```

이 예제에서:
- `text`는 입력 컬럼입니다 (프롬프트에서 `{text}`로 참조)
- `expected_output`은 심사자가 비교할 대상입니다

### 다중 컬럼 입력

여러 입력 컬럼을 가질 수 있습니다:

```csv
source_lang,target_lang,text,expected_output
"en","fr","Hello","Bonjour"
"en","es","Hello","Hola"
```

프롬프트 예제: `Translate from {source_lang} to {target_lang}: {text}`

## API 참조

### 실행 관리

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `POST` | `/api/runs` | 새 최적화 실행 생성 (multipart form) |
| `GET` | `/api/runs` | 모든 실행 목록 (생성 날짜순) |
| `GET` | `/api/runs/{id}` | 반복이 포함된 실행 세부 정보 가져오기 |
| `DELETE` | `/api/runs/{id}` | 실행 및 모든 관련 데이터 삭제 |
| `POST` | `/api/runs/{id}/stop` | 실행 중인 최적화 중지 |
| `POST` | `/api/runs/{id}/feedback` | 실행 중인 파이프라인에 휴먼 피드백 제출 |

### 프로바이더 관리

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `GET` | `/api/providers` | 모든 프로바이더 목록 (구성 상태 및 기본값 포함) |
| `GET` | `/api/providers/{id}/models` | 프로바이더의 사용 가능한 모델 목록 |
| `POST` | `/api/providers/custom/models` | 사용자 정의 엔드포인트에서 모델 목록 |

### 반복 데이터

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `GET` | `/api/runs/{id}/iterations` | 실행의 모든 반복 목록 |
| `GET` | `/api/runs/{id}/iterations/{num}` | 테스트 결과가 포함된 반복 세부 정보 가져오기 |

### 로그 및 이벤트

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `GET` | `/api/runs/{id}/logs` | 로그 가져오기 (단계 및 레벨별 필터링 가능) |
| `GET` | `/api/runs/{id}/stream` | 실시간 업데이트를 위한 Server-Sent Events 스트림 |

### 요청 형식: 실행 생성

```bash
curl -X POST http://localhost:8000/api/runs \
  -F "file=@test_data.csv" \
  -F "name=My Translation Test" \
  -F "initial_prompt=Translate to French: {text}" \
  -F "expected_column=expected_output" \
  -F 'config_json={"model":"gpt-4o-mini","max_iterations":10,"target_score":0.9}'
```

### SSE 이벤트 유형

`/api/runs/{id}/stream` 엔드포인트는 다음 이벤트를 발생시킵니다:

- `stage_start` - 파이프라인 단계 시작 (test, judge, summarize, improve)
- `test_progress` - 테스트 단계 진행 업데이트
- `iteration_complete` - 점수와 함께 반복 완료
- `feedback_requested` - 피드백 요청 (반복 완료 후 피드백 대기)
- `converged` - 파이프라인 수렴 (목표 도달 또는 정체)
- `completed` - 파이프라인 완료 (최대 반복 도달)
- `stopped` - 사용자가 파이프라인 중지
- `failed` - 파이프라인에 오류 발생

## 기술 스택

### 백엔드
- **FastAPI** - 최신 비동기 웹 프레임워크
- **SQLAlchemy 2.0** - 관계 로딩이 있는 비동기 ORM
- **SQLite** - 비동기 지원이 있는 임베디드 데이터베이스 (aiosqlite)
- **OpenAI Python SDK** - 멀티 프로바이더 지원이 있는 LLM 클라이언트
- **Anthropic Python SDK** - 네이티브 Claude API 클라이언트
- **Pydantic** - 데이터 검증 및 설정 관리

### 프론트엔드
- **React 18** - 동시 기능이 있는 UI 프레임워크
- **TypeScript** - 타입 안전 개발
- **Vite** - 빠른 빌드 도구 및 개발 서버
- **TailwindCSS** - 유틸리티 우선 스타일링
- **React Query** - 캐싱이 있는 서버 상태 관리
- **React Router** - 클라이언트 측 라우팅
- **Recharts** - 선언적 차트 라이브러리
- **Axios** - HTTP 클라이언트

### 실시간 통신
- **Server-Sent Events (SSE)** - 서버에서 클라이언트로의 실시간 진행 업데이트

## 테스트 실행

프로젝트에는 멀티 프로바이더 기능과 전체 최적화 파이프라인을 검증하는 포괄적인 테스트 스위트가 포함되어 있습니다.

### 유닛 테스트

멀티 프로바이더 로직에 대한 51개의 유닛 테스트 (서버 불필요):

```bash
python3 -m pytest tests/test_multi_provider.py -v
```

테스트 범위:
- 프로바이더 등록 및 디스커버리
- 모델 필터링 및 검증
- LLM 클라이언트 생성
- 재시도 로직
- 오류 처리
- 설정 마이그레이션

### E2E 테스트

전체 파이프라인 테스트 (실행 중인 서버 필요):

```bash
# 백엔드 서버 시작
python3 -m uvicorn backend.main:app --reload --port 8000

# 새 터미널에서
python3 tests/test_e2e.py
python3 tests/test_e2e_multi_column.py
```

테스트 스위트에는 다음이 포함됩니다:
- CSV 업로드로 실행 생성
- 파이프라인 진행 모니터링
- 반복 점수 검증
- 프롬프트 개선 확인
- 수렴 동작 검증
- 중지 기능 테스트
- 다중 컬럼 입력 처리
- 데이터 정리 검증

## 수렴 기준

파이프라인은 다음 조건 중 하나가 충족되면 최적화를 중지합니다:

### 1. 목표 점수 도달
- 모든 테스트 케이스의 평균 점수가 구성된 목표 점수에 도달하거나 초과
- 기본 목표: 0.9 (90% 품질)
- 실행당 구성 가능

### 2. 점수 정체
- 점수 개선이 여러 연속 반복에 대해 수렴 임계값 미만으로 떨어짐
- 기본 임계값: 0.02 (2% 개선)
- 기본 인내: 2회 연속 라운드
- 두 값 모두 구성 가능

### 3. 최대 반복 도달
- 파이프라인이 구성된 최대 반복 횟수를 완료
- 기본값: 10회 반복
- 실행당 구성 가능

### 수렴 감지 예제

```
Iteration 1: avg_score = 0.65
Iteration 2: avg_score = 0.78 (improvement: 0.13)
Iteration 3: avg_score = 0.85 (improvement: 0.07)
Iteration 4: avg_score = 0.86 (improvement: 0.01) <- 임계값 미만
Iteration 5: avg_score = 0.865 (improvement: 0.005) <- 임계값 미만
→ 정체로 인한 수렴 (2회 연속 라운드가 0.02 미만)
```

## 프로젝트 기능

### 실시간 진행 추적
- Server-Sent Events를 통한 실시간 업데이트
- 테스트 실행을 위한 진행률 표시줄
- 현재 파이프라인 단계를 표시하는 단계 표시기

### 상세 분석
- 개선 추세를 보여주는 점수 차트
- 반복별 비교
- 심사자 추론이 포함된 테스트 수준 결과
- 단계 및 레벨별 필터링 가능한 로그

### 프롬프트 엔지니어링 인사이트
- 나란히 프롬프트 비교
- LLM의 개선 추론
- 실패 패턴 요약
- 각 테스트 케이스에 대한 심사자 피드백

### 유연한 구성
- 도메인별 채점을 위한 사용자 지정 심사 프롬프트
- 조정 가능한 수렴 기준
- 파이프라인 단계별 모델 선택
- 비용/속도 트레이드오프를 위한 동시성 제어
- 멀티 프로바이더 지원 (OpenAI, Gemini, Anthropic)

### 휴먼 피드백
- 실행 설정에서 `human_feedback_enabled` 활성화
- 각 반복의 요약 단계 후 파이프라인 일시 중지
- 사용자가 개선자에 통합될 서면 피드백 제공 가능
- 30분 타임아웃 후 자동 계속
- 피드백은 다음 개선 프롬프트에 포함되어 사용자 요구사항 반영

## 문제 해결

### 백엔드가 시작되지 않음
- 포트 8000이 사용 중이 아닌지 확인
- `OPENAI_API_KEY`가 있는 `.env` 파일이 존재하는지 확인
- 모든 의존성이 설치되었는지 확인: `pip3 install -r backend/requirements.txt`

### 프론트엔드가 시작되지 않음
- 포트 5173이 사용 중이 아닌지 확인
- Node.js 버전이 18+ 인지 확인
- `node_modules`를 삭제하고 재설치: `rm -rf node_modules && npm install`

### CSV 업로드 실패
- CSV에 최소 2개의 컬럼이 있는지 확인 (1개 입력 + 1개 예상 출력)
- 컬럼 이름에 특수 문자가 없는지 확인
- 파일 인코딩이 UTF-8인지 확인

### 파이프라인이 즉시 실패
- API 키가 유효하고 크레딧이 있는지 확인
- `OPENAI_BASE_URL`이 제공업체와 일치하는지 확인
- 특정 오류 메시지는 실행 세부 정보 페이지의 로그를 검토

### 실시간 업데이트 없음
- 브라우저가 Server-Sent Events를 지원하는지 확인 (모든 최신 브라우저 지원)
- 연결 오류는 브라우저 콘솔 확인
- 백엔드가 실행 중이고 액세스 가능한지 확인

## 라이선스

이 프로젝트는 교육 및 상업적 사용을 위해 있는 그대로 제공됩니다.

## 지원

문제, 질문 또는 기여에 대해서는 프로젝트 리포지토리를 참조하거나 개발팀에 문의하세요.
