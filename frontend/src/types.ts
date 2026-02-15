export interface RunConfig {
  model?: string
  model_provider?: string
  judge_model?: string
  judge_provider?: string
  improver_model?: string
  improver_provider?: string
  max_iterations: number
  target_score: number
  temperature: number
  concurrency: number
  judge_prompt?: string
  convergence_threshold: number
  convergence_patience: number
  human_feedback_enabled?: boolean
  summary_language?: string
}

export interface Run {
  id: number
  name: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'stopped'
  initial_prompt: string
  best_prompt: string | null
  best_score: number | null
  config: RunConfig
  dataset_filename: string
  dataset_columns: string[]
  total_iterations_completed: number
  error_message: string | null
  created_at: string
}

export interface Iteration {
  id: number
  run_id: number
  iteration_num: number
  prompt_template: string
  avg_score: number | null
  min_score: number | null
  max_score: number | null
  summary: string | null
  improvement_reasoning: string | null
  improver_prompt: string | null
  created_at: string
}

export interface TestResult {
  id: number
  iteration_id: number
  test_case_index: number
  input_data: Record<string, string>
  expected_output: string
  actual_output: string | null
  score: number | null
  judge_reasoning: string | null
  created_at: string
}

export interface LogEntry {
  id: number
  run_id: number
  iteration_id: number | null
  stage: 'test' | 'judge' | 'summarize' | 'improve' | 'system'
  level: 'info' | 'warn' | 'error'
  message: string
  data: Record<string, any> | null
  created_at: string
}

export interface RunDetail extends Run {
  iterations: Iteration[]
}

export interface IterationDetail extends Iteration {
  test_results: TestResult[]
}

export interface SSEEvent {
  event: string
  data: Record<string, any>
}

export interface Provider {
  id: string
  name: string
  configured: boolean
}

export interface ProviderDefaults {
  model: string
  model_provider: string
  judge_model: string
  judge_provider: string
  improver_model: string
  improver_provider: string
}

export interface ProvidersResponse {
  providers: Provider[]
  defaults: ProviderDefaults
}

export interface ProviderModelsResponse {
  models: string[]
  error?: string
}

export interface FeedbackRequest {
  iteration: number
  summary: {
    avg_score: number
    min_score: number
    max_score: number
    summary: string
    failure_patterns: string[]
    specific_issues: string[]
    suggestions: string[]
  }
}
