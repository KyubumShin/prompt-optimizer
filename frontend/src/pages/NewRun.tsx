import { useState, useCallback, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useCreateRun } from '../hooks/useRuns'
import { fetchModels, fetchCustomModels } from '../lib/api'

interface CSVPreview {
  columns: string[]
  rows: string[][]
}

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
    judge_model: '',
    improver_model: '',
    max_iterations: 10,
    target_score: 0.9,
    temperature: 0.7,
    concurrency: 5,
    judge_prompt: '',
    convergence_threshold: 0.02,
    convergence_patience: 2,
  })
  const [error, setError] = useState('')
  const [availableModels, setAvailableModels] = useState<string[]>([])
  const [modelDefaults, setModelDefaults] = useState<{ model: string; judge_model: string; improver_model: string } | null>(null)
  const [modelsLoading, setModelsLoading] = useState(false)
  const [modelsError, setModelsError] = useState('')
  const [useCustomUrl, setUseCustomUrl] = useState(false)
  const [customBaseUrl, setCustomBaseUrl] = useState('')
  const [customApiKey, setCustomApiKey] = useState('')

  useEffect(() => {
    if (step === 3 && !useCustomUrl && availableModels.length === 0 && !modelsLoading) {
      setModelsLoading(true)
      setModelsError('')
      fetchModels()
        .then((res) => {
          if (res.error) {
            setModelsError(res.error)
          } else {
            setAvailableModels(res.models)
            setModelDefaults(res.defaults)
          }
        })
        .catch((e) => setModelsError(e.message || 'Failed to fetch models'))
        .finally(() => setModelsLoading(false))
    }
  }, [step])

  const handleFetchCustomModels = async () => {
    if (!customBaseUrl.trim()) return
    setModelsLoading(true)
    setModelsError('')
    try {
      const res = await fetchCustomModels(customBaseUrl, customApiKey || undefined)
      if (res.error) {
        setModelsError(res.error)
        setAvailableModels([])
      } else {
        setAvailableModels(res.models)
        setModelDefaults(null)
      }
    } catch (e: any) {
      setModelsError(e.message || 'Failed to fetch models')
      setAvailableModels([])
    } finally {
      setModelsLoading(false)
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
      const columns = lines[0].split(',').map((c) => c.trim().replace(/^"|"$/g, ''))
      const rows = lines.slice(1, 6).map((line) =>
        line.split(',').map((c) => c.trim().replace(/^"|"$/g, ''))
      )
      setCsvPreview({ columns, rows })
      setExpectedColumn(columns[columns.length - 1])
      setError('')
    }
    reader.readAsText(f)
  }, [])

  const insertPlaceholder = (col: string) => {
    setPrompt((prev) => prev + `{${col}}`)
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
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Test Model</label>
              <select value={config.model} onChange={(e) => setConfig({ ...config, model: e.target.value })}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm bg-white">
                <option value="">{modelDefaults ? `Server default (${modelDefaults.model})` : 'Server default'}</option>
                {availableModels.map((m) => <option key={m} value={m}>{m}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Judge Model</label>
              <select value={config.judge_model} onChange={(e) => setConfig({ ...config, judge_model: e.target.value })}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm bg-white">
                <option value="">{modelDefaults ? `Server default (${modelDefaults.judge_model})` : 'Server default'}</option>
                {availableModels.map((m) => <option key={m} value={m}>{m}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Improver Model</label>
              <select value={config.improver_model} onChange={(e) => setConfig({ ...config, improver_model: e.target.value })}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm bg-white">
                <option value="">{modelDefaults ? `Server default (${modelDefaults.improver_model})` : 'Server default'}</option>
                {availableModels.map((m) => <option key={m} value={m}>{m}</option>)}
              </select>
            </div>
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
          {/* Custom URL toggle */}
          <div className="border border-gray-200 rounded-lg p-4 space-y-3">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={useCustomUrl}
                onChange={(e) => {
                  setUseCustomUrl(e.target.checked)
                  if (!e.target.checked) {
                    setCustomBaseUrl('')
                    setCustomApiKey('')
                    setAvailableModels([])
                    setModelDefaults(null)
                    setModelsError('')
                    setModelsLoading(true)
                    fetchModels()
                      .then((res) => {
                        if (res.error) {
                          setModelsError(res.error)
                        } else {
                          setAvailableModels(res.models)
                          setModelDefaults(res.defaults)
                        }
                      })
                      .catch((e) => setModelsError(e.message || 'Failed to fetch models'))
                      .finally(() => setModelsLoading(false))
                  }
                }}
                className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
              />
              <span className="text-sm font-medium text-gray-700">Use Custom OpenAI-Compatible URL</span>
            </label>
            {useCustomUrl && (
              <div className="space-y-2">
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
                  disabled={!customBaseUrl.trim() || modelsLoading}
                  className="px-4 py-1.5 bg-gray-100 text-gray-700 rounded-lg text-sm hover:bg-gray-200 disabled:opacity-50"
                >
                  {modelsLoading ? 'Fetching...' : 'Fetch Models'}
                </button>
              </div>
            )}
            {modelsLoading && !useCustomUrl && (
              <p className="text-xs text-gray-500">Loading available models...</p>
            )}
            {modelsError && (
              <p className="text-xs text-red-500">Error: {modelsError}</p>
            )}
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Custom Judge Prompt (optional)</label>
            <textarea
              value={config.judge_prompt}
              onChange={(e) => setConfig({ ...config, judge_prompt: e.target.value })}
              rows={4}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono"
              placeholder="Leave empty for default judge prompt. Use {input_data}, {expected}, {actual} placeholders."
            />
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
