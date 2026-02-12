import { useState, useCallback, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useCreateRun } from '../hooks/useRuns'
import { fetchProviders, fetchProviderModels, fetchCustomProviderModels } from '../lib/api'
import type { Provider, ProviderDefaults } from '../types'

interface CSVPreview {
  columns: string[]
  rows: string[][]
}

type StageKey = 'model' | 'judge' | 'improver'

/** Parse a single CSV line respecting quoted fields (handles commas inside quotes). */
function parseCSVLine(line: string): string[] {
  const fields: string[] = []
  let current = ''
  let inQuotes = false

  for (let i = 0; i < line.length; i++) {
    const ch = line[i]
    if (inQuotes) {
      if (ch === '"') {
        if (i + 1 < line.length && line[i + 1] === '"') {
          current += '"'
          i++ // skip escaped quote
        } else {
          inQuotes = false
        }
      } else {
        current += ch
      }
    } else {
      if (ch === '"') {
        inQuotes = true
      } else if (ch === ',') {
        fields.push(current.trim())
        current = ''
      } else {
        current += ch
      }
    }
  }
  fields.push(current.trim())
  return fields
}

const DEFAULT_JUDGE_PROMPT = `You are an expert judge evaluating the quality of an AI-generated response.

Given:
- Input: {input_data}
- Expected Output: {expected}
- Actual Output: {actual}

Evaluate the actual output against the expected output. Consider:
1. Correctness: Does it match the expected output semantically?
2. Completeness: Does it cover all required information?
3. Format: Is it in the right format?

Respond with ONLY a JSON object:
{"reason": "your detailed reasoning here", "score": 0.0}

Score should be between 0.0 (completely wrong) and 1.0 (perfect match).`

export default function NewRun() {
  const navigate = useNavigate()
  const createRun = useCreateRun()

  const [step, setStep] = useState(1)
  const [file, setFile] = useState<File | null>(null)
  const [csvPreview, setCsvPreview] = useState<CSVPreview | null>(null)
  const [name, setName] = useState('')
  const [prompt, setPrompt] = useState('')
  const [expectedColumn, setExpectedColumn] = useState('')
  const [config, setConfig] = useState({
    model: '',
    model_provider: '',
    judge_model: '',
    judge_provider: '',
    improver_model: '',
    improver_provider: '',
    max_iterations: 10,
    target_score: 0.9,
    temperature: 0.7,
    concurrency: 5,
    judge_prompt: '',
    convergence_threshold: 0.02,
    convergence_patience: 2,
    human_feedback_enabled: false,
    summary_language: 'English',
  })
  const [error, setError] = useState('')

  // Provider state
  const [providers, setProviders] = useState<Provider[]>([])
  const [defaults, setDefaults] = useState<ProviderDefaults | null>(null)
  const [providersLoading, setProvidersLoading] = useState(false)
  const [providersError, setProvidersError] = useState('')

  // Per-provider model cache: { providerId: string[] }
  const [modelCache, setModelCache] = useState<Record<string, string[]>>({})
  const [modelsLoading, setModelsLoading] = useState<Record<string, boolean>>({})
  const [modelsError, setModelsError] = useState<Record<string, string>>({})

  // Custom provider state
  const [customBaseUrl, setCustomBaseUrl] = useState('')
  const [customApiKey, setCustomApiKey] = useState('')

  // Load providers when entering step 3
  useEffect(() => {
    if (step === 3 && providers.length === 0 && !providersLoading) {
      setProvidersLoading(true)
      setProvidersError('')
      fetchProviders()
        .then((res) => {
          setProviders(res.providers)
          setDefaults(res.defaults)
          // Set default providers if not already set
          setConfig((prev) => ({
            ...prev,
            model_provider: prev.model_provider || res.defaults.model_provider,
            judge_provider: prev.judge_provider || res.defaults.judge_provider,
            improver_provider: prev.improver_provider || res.defaults.improver_provider,
          }))
        })
        .catch((e) => setProvidersError(e.message || 'Failed to fetch providers'))
        .finally(() => setProvidersLoading(false))
    }
  }, [step])

  // Load models when a provider is selected (for any stage)
  const loadModelsForProvider = useCallback(async (providerId: string) => {
    if (!providerId || modelCache[providerId] || modelsLoading[providerId]) return
    if (providerId === 'custom') return // Custom handled separately

    setModelsLoading((prev) => ({ ...prev, [providerId]: true }))
    setModelsError((prev) => ({ ...prev, [providerId]: '' }))
    try {
      const res = await fetchProviderModels(providerId)
      if (res.error) {
        setModelsError((prev) => ({ ...prev, [providerId]: res.error! }))
      } else {
        setModelCache((prev) => ({ ...prev, [providerId]: res.models }))
      }
    } catch (e: any) {
      setModelsError((prev) => ({ ...prev, [providerId]: e.message || 'Failed to fetch models' }))
    } finally {
      setModelsLoading((prev) => ({ ...prev, [providerId]: false }))
    }
  }, [modelCache, modelsLoading])

  // Auto-load models for default providers when defaults are set
  useEffect(() => {
    if (defaults) {
      const uniqueProviders = new Set([defaults.model_provider, defaults.judge_provider, defaults.improver_provider])
      uniqueProviders.forEach((pid) => {
        if (pid && pid !== 'custom') loadModelsForProvider(pid)
      })
    }
  }, [defaults])

  const handleProviderChange = (stage: StageKey, providerId: string) => {
    const providerKey = stage === 'model' ? 'model_provider' : stage === 'judge' ? 'judge_provider' : 'improver_provider'
    const modelKey = stage === 'model' ? 'model' : stage === 'judge' ? 'judge_model' : 'improver_model'
    setConfig((prev) => ({ ...prev, [providerKey]: providerId, [modelKey]: '' }))
    if (providerId !== 'custom') {
      loadModelsForProvider(providerId)
    }
  }

  const handleModelChange = (stage: StageKey, model: string) => {
    const modelKey = stage === 'model' ? 'model' : stage === 'judge' ? 'judge_model' : 'improver_model'
    setConfig((prev) => ({ ...prev, [modelKey]: model }))
  }

  const handleFetchCustomModels = async () => {
    if (!customBaseUrl.trim()) return
    setModelsLoading((prev) => ({ ...prev, custom: true }))
    setModelsError((prev) => ({ ...prev, custom: '' }))
    try {
      const res = await fetchCustomProviderModels(customBaseUrl, customApiKey || undefined)
      if (res.error) {
        setModelsError((prev) => ({ ...prev, custom: res.error! }))
        setModelCache((prev) => ({ ...prev, custom: [] }))
      } else {
        setModelCache((prev) => ({ ...prev, custom: res.models }))
      }
    } catch (e: any) {
      setModelsError((prev) => ({ ...prev, custom: e.message || 'Failed to fetch models' }))
      setModelCache((prev) => ({ ...prev, custom: [] }))
    } finally {
      setModelsLoading((prev) => ({ ...prev, custom: false }))
    }
  }

  const handleFileUpload = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]
    if (!f) return
    setFile(f)
    setName(f.name.replace(/\.csv$/i, ''))

    const reader = new FileReader()
    reader.onload = (evt) => {
      const text = evt.target?.result as string
      const lines = text.split('\n').filter((l) => l.trim())
      if (lines.length < 2) {
        setError('CSV must have a header and at least one data row')
        return
      }
      const columns = parseCSVLine(lines[0])
      const rows = lines.slice(1, 6).map((line) => parseCSVLine(line))
      setCsvPreview({ columns, rows })
      setExpectedColumn(columns[columns.length - 1])
      setError('')
    }
    reader.readAsText(f)
  }, [])

  const insertPlaceholder = (col: string) => {
    setPrompt((prev) => prev + `{${col}}`)
  }

  const insertJudgePlaceholder = (placeholder: string) => {
    setConfig((prev) => ({ ...prev, judge_prompt: prev.judge_prompt + placeholder }))
  }

  const handleSubmit = async () => {
    if (!file) return
    setError('')
    try {
      const formData = new FormData()
      formData.append('name', name)
      formData.append('initial_prompt', prompt)
      formData.append('expected_column', expectedColumn)
      formData.append('file', file)
      const configToSend = { ...config }
      if (!configToSend.judge_prompt) {
        const { judge_prompt, ...rest } = configToSend as any
        formData.append('config_json', JSON.stringify(rest))
      } else {
        formData.append('config_json', JSON.stringify(configToSend))
      }
      const run = await createRun.mutateAsync(formData)
      navigate(`/runs/${run.id}`)
    } catch (e: any) {
      setError(e?.response?.data?.detail || e.message || 'Failed to create run')
    }
  }

  const inputColumns = csvPreview ? csvPreview.columns.filter((c) => c !== expectedColumn) : []

  // Helper to get provider info for a stage
  const getStageProvider = (stage: StageKey): string => {
    if (stage === 'model') return config.model_provider
    if (stage === 'judge') return config.judge_provider
    return config.improver_provider
  }

  const getStageModel = (stage: StageKey): string => {
    if (stage === 'model') return config.model
    if (stage === 'judge') return config.judge_model
    return config.improver_model
  }

  const getDefaultModel = (stage: StageKey): string => {
    if (!defaults) return ''
    if (stage === 'model') return defaults.model
    if (stage === 'judge') return defaults.judge_model
    return defaults.improver_model
  }

  const renderProviderModelSelector = (stage: StageKey, label: string) => {
    const providerId = getStageProvider(stage)
    const modelValue = getStageModel(stage)
    const defaultModel = getDefaultModel(stage)
    const models = modelCache[providerId] || []
    const loading = modelsLoading[providerId] || false
    const errorMsg = modelsError[providerId] || ''
    const isCustom = providerId === 'custom'

    return (
      <div className="border border-gray-200 rounded-lg p-3 space-y-2">
        <label className="block text-xs font-semibold text-gray-700">{label}</label>
        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="block text-xs text-gray-500 mb-1">Provider</label>
            <select
              value={providerId}
              onChange={(e) => handleProviderChange(stage, e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm bg-white"
            >
              <option value="">Select provider...</option>
              {providers.map((p) => (
                <option key={p.id} value={p.id} disabled={!p.configured && p.id !== 'custom'}>
                  {p.name}{!p.configured && p.id !== 'custom' ? ' (not configured)' : ''}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Model</label>
            {isCustom ? (
              <>
                <input
                  type="text"
                  list={`custom-models-${stage}`}
                  value={modelValue}
                  onChange={(e) => handleModelChange(stage, e.target.value)}
                  placeholder="Type model name..."
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                />
                {models.length > 0 && (
                  <datalist id={`custom-models-${stage}`}>
                    {models.map((m) => (
                      <option key={m} value={m} />
                    ))}
                  </datalist>
                )}
              </>
            ) : (
              <select
                value={modelValue}
                onChange={(e) => handleModelChange(stage, e.target.value)}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm bg-white"
                disabled={!providerId || loading}
              >
                <option value="">
                  {loading ? 'Loading...' : defaultModel ? `Default (${defaultModel})` : 'Select model...'}
                </option>
                {models.map((m) => (
                  <option key={m} value={m}>
                    {m}{m === defaultModel ? ' (default)' : ''}
                  </option>
                ))}
              </select>
            )}
          </div>
        </div>
        {errorMsg && <p className="text-xs text-red-500">{errorMsg}</p>}
      </div>
    )
  }

  // Check if any stage uses custom provider
  const anyCustom = config.model_provider === 'custom' || config.judge_provider === 'custom' || config.improver_provider === 'custom'

  return (
    <div className="max-w-3xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">New Optimization Run</h1>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-4 text-sm">
          {error}
        </div>
      )}

      {/* Step indicators */}
      <div className="flex items-center gap-2 mb-8">
        {[1, 2, 3].map((s) => (
          <div key={s} className="flex items-center">
            <div
              className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                step >= s ? 'bg-indigo-600 text-white' : 'bg-gray-200 text-gray-500'
              }`}
            >
              {s}
            </div>
            {s < 3 && <div className={`w-16 h-0.5 mx-1 ${step > s ? 'bg-indigo-600' : 'bg-gray-200'}`} />}
          </div>
        ))}
        <span className="text-sm text-gray-500 ml-2">
          {step === 1 ? 'Upload Data' : step === 2 ? 'Write Prompt' : 'Configure'}
        </span>
      </div>

      {/* Step 1: Upload CSV */}
      {step === 1 && (
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Upload CSV Dataset</label>
            <input
              type="file"
              accept=".csv"
              onChange={handleFileUpload}
              className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100"
            />
          </div>

          {csvPreview && (
            <>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Run Name</label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Expected Output Column</label>
                <select
                  value={expectedColumn}
                  onChange={(e) => setExpectedColumn(e.target.value)}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500"
                >
                  {csvPreview.columns.map((col) => (
                    <option key={col} value={col}>{col}</option>
                  ))}
                </select>
              </div>

              <div>
                <h3 className="text-sm font-medium text-gray-700 mb-2">Preview (first 5 rows)</h3>
                <div className="overflow-x-auto border rounded-lg">
                  <table className="w-full text-xs">
                    <thead className="bg-gray-50">
                      <tr>
                        {csvPreview.columns.map((col) => (
                          <th key={col} className="px-3 py-2 text-left font-medium text-gray-600">
                            {col} {col === expectedColumn && <span className="text-indigo-500">(expected)</span>}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {csvPreview.rows.map((row, i) => (
                        <tr key={i} className="border-t">
                          {row.map((cell, j) => (
                            <td key={j} className="px-3 py-2 text-gray-700 max-w-[200px] truncate">{cell}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          )}

          <button
            onClick={() => setStep(2)}
            disabled={!csvPreview || !name}
            className="bg-indigo-600 text-white px-6 py-2 rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium"
          >
            Next: Write Prompt
          </button>
        </div>
      )}

      {/* Step 2: Write Prompt */}
      {step === 2 && (
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Prompt Template
            </label>
            <p className="text-xs text-gray-500 mb-2">
              Use {'{column_name}'} placeholders to insert CSV values. Click a column name below to insert it.
            </p>
            <div className="flex flex-wrap gap-1 mb-2">
              {inputColumns.map((col) => (
                <button
                  key={col}
                  onClick={() => insertPlaceholder(col)}
                  className="px-2 py-1 bg-indigo-50 text-indigo-700 rounded text-xs hover:bg-indigo-100"
                >
                  {'{' + col + '}'}
                </button>
              ))}
            </div>
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              rows={10}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              placeholder={`e.g., Translate the following text to French:\n\n{text}`}
            />
          </div>
          <div className="flex gap-3">
            <button onClick={() => setStep(1)} className="px-6 py-2 border border-gray-300 rounded-lg text-sm text-gray-700 hover:bg-gray-50">
              Back
            </button>
            <button
              onClick={() => setStep(3)}
              disabled={!prompt.trim()}
              className="bg-indigo-600 text-white px-6 py-2 rounded-lg hover:bg-indigo-700 disabled:opacity-50 text-sm font-medium"
            >
              Next: Configure
            </button>
          </div>
        </div>
      )}

      {/* Step 3: Configure Settings */}
      {step === 3 && (
        <div className="space-y-4">
          {providersLoading && (
            <p className="text-xs text-gray-500">Loading providers...</p>
          )}
          {providersError && (
            <p className="text-xs text-red-500">Error loading providers: {providersError}</p>
          )}

          {/* Provider + Model selectors per stage */}
          <div className="space-y-3">
            {renderProviderModelSelector('model', 'Test Model')}
            {renderProviderModelSelector('judge', 'Judge Model')}
            {renderProviderModelSelector('improver', 'Improver Model')}
          </div>

          {/* Custom endpoint config (shown if any stage uses custom) */}
          {anyCustom && (
            <div className="border border-amber-200 bg-amber-50 rounded-lg p-4 space-y-2">
              <label className="block text-sm font-medium text-amber-800">Custom Endpoint Configuration</label>
              <input
                type="text"
                value={customBaseUrl}
                onChange={(e) => setCustomBaseUrl(e.target.value)}
                placeholder="https://api.example.com/v1"
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
              />
              <input
                type="password"
                value={customApiKey}
                onChange={(e) => setCustomApiKey(e.target.value)}
                placeholder="API Key (optional, uses server key if empty)"
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
              />
              <button
                onClick={handleFetchCustomModels}
                disabled={!customBaseUrl.trim() || modelsLoading['custom']}
                className="px-4 py-1.5 bg-amber-100 text-amber-800 rounded-lg text-sm hover:bg-amber-200 disabled:opacity-50"
              >
                {modelsLoading['custom'] ? 'Fetching...' : 'Fetch Models'}
              </button>
            </div>
          )}

          {/* Hyperparameters */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Max Iterations</label>
              <input type="number" value={config.max_iterations} onChange={(e) => setConfig({ ...config, max_iterations: parseInt(e.target.value) || 10 })}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Target Score (0-1)</label>
              <input type="number" step="0.05" value={config.target_score} onChange={(e) => setConfig({ ...config, target_score: parseFloat(e.target.value) || 0.9 })}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Temperature</label>
              <input type="number" step="0.1" value={config.temperature} onChange={(e) => setConfig({ ...config, temperature: parseFloat(e.target.value) || 0.7 })}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Concurrency</label>
              <input type="number" value={config.concurrency} onChange={(e) => setConfig({ ...config, concurrency: parseInt(e.target.value) || 5 })}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Convergence Patience</label>
              <input type="number" value={config.convergence_patience} onChange={(e) => setConfig({ ...config, convergence_patience: parseInt(e.target.value) || 2 })}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Custom Judge Prompt (optional)
            </label>
            <p className="text-xs text-gray-500 mb-2">
              Customize how the judge evaluates responses. Use placeholders to inject data. Leave empty to use the default prompt shown below.
            </p>
            <div className="flex flex-wrap gap-1 mb-2">
              {['{input_data}', '{expected}', '{actual}'].map((ph) => (
                <button
                  key={ph}
                  onClick={() => insertJudgePlaceholder(ph)}
                  className="px-2 py-1 bg-indigo-50 text-indigo-700 rounded text-xs hover:bg-indigo-100"
                >
                  {ph}
                </button>
              ))}
              <button
                onClick={() => setConfig((prev) => ({ ...prev, judge_prompt: DEFAULT_JUDGE_PROMPT }))}
                className="ml-auto px-2 py-1 bg-gray-100 text-gray-600 rounded text-xs hover:bg-gray-200"
              >
                Reset to default
              </button>
            </div>
            <textarea
              value={config.judge_prompt}
              onChange={(e) => setConfig({ ...config, judge_prompt: e.target.value })}
              rows={10}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              placeholder={DEFAULT_JUDGE_PROMPT}
            />
          </div>

          {/* Human Feedback Toggle */}
          <div className="flex items-center justify-between p-3 border border-gray-200 rounded-lg">
            <div>
              <label className="block text-xs font-medium text-gray-600">Human Feedback</label>
              <p className="text-xs text-gray-400 mt-0.5">Pause after each summary for your review before improving</p>
            </div>
            <button
              type="button"
              onClick={() => setConfig({ ...config, human_feedback_enabled: !config.human_feedback_enabled })}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                config.human_feedback_enabled ? 'bg-indigo-600' : 'bg-gray-200'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  config.human_feedback_enabled ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>

          {/* Summary Language */}
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Summary Language</label>
            <select
              value={config.summary_language}
              onChange={(e) => setConfig({ ...config, summary_language: e.target.value })}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
            >
              {['English', 'Korean', 'Japanese', 'Chinese', 'Spanish', 'French', 'German', 'Portuguese'].map((lang) => (
                <option key={lang} value={lang}>{lang}</option>
              ))}
            </select>
          </div>

          <div className="flex gap-3">
            <button onClick={() => setStep(2)} className="px-6 py-2 border border-gray-300 rounded-lg text-sm text-gray-700 hover:bg-gray-50">
              Back
            </button>
            <button
              onClick={handleSubmit}
              disabled={createRun.isPending}
              className="bg-indigo-600 text-white px-6 py-2 rounded-lg hover:bg-indigo-700 disabled:opacity-50 text-sm font-medium"
            >
              {createRun.isPending ? 'Creating...' : 'Start Optimization'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
