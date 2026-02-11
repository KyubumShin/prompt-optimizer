import { useState, useCallback } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useRun, useStopRun, useLogs } from '../hooks/useRuns'
import { useSSE } from '../hooks/useSSE'
import { submitFeedback } from '../lib/api'
import StatusBadge from '../components/StatusBadge'
import ScoreChart from '../components/ScoreChart'
import PromptDiff from '../components/PromptDiff'
import LogViewer from '../components/LogViewer'
import type { SSEEvent, FeedbackRequest } from '../types'

export default function RunDetail() {
  const { id } = useParams<{ id: string }>()
  const runId = Number(id)
  const { data: run, isLoading, refetch } = useRun(runId)
  const stopRun = useStopRun()
  const { data: logs } = useLogs(runId)

  const [liveStatus, setLiveStatus] = useState<string>('')
  const [diffLeft, setDiffLeft] = useState<number | null>(null)
  const [diffRight, setDiffRight] = useState<number | null>(null)
  const [copied, setCopied] = useState(false)
  const [feedbackRequested, setFeedbackRequested] = useState(false)
  const [feedbackText, setFeedbackText] = useState('')
  const [feedbackSummary, setFeedbackSummary] = useState<FeedbackRequest | null>(null)
  const [submittingFeedback, setSubmittingFeedback] = useState(false)

  const handleSSE = useCallback((event: SSEEvent) => {
    switch (event.event) {
      case 'stage_start':
        setLiveStatus(`Iteration ${event.data.iteration}: ${event.data.stage}...`)
        break
      case 'test_progress':
        setLiveStatus(`Testing: ${event.data.completed}/${event.data.total}`)
        break
      case 'iteration_complete':
        setLiveStatus(`Iteration ${event.data.iteration} done: ${(event.data.avg_score * 100).toFixed(1)}%`)
        refetch()
        break
      case 'feedback_requested':
        setFeedbackRequested(true)
        setFeedbackSummary(event.data as FeedbackRequest)
        setLiveStatus(`Iteration ${event.data.iteration}: Waiting for feedback...`)
        break
      case 'completed':
      case 'converged':
      case 'failed':
      case 'stopped':
        setLiveStatus('')
        refetch()
        break
    }
  }, [refetch])

  useSSE(runId, handleSSE, run?.status === 'running' || run?.status === 'pending')

  if (isLoading) return <div className="text-center py-12 text-gray-400">Loading...</div>
  if (!run) return <div className="text-center py-12 text-gray-400">Run not found</div>

  const iterations = run.iterations || []
  const sortedIterations = [...iterations].sort((a, b) => a.iteration_num - b.iteration_num)

  const handleCopyBest = () => {
    if (run.best_prompt) {
      navigator.clipboard.writeText(run.best_prompt)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  const handleSubmitFeedback = async () => {
    setSubmittingFeedback(true)
    try {
      await submitFeedback(runId, feedbackText)
      setFeedbackRequested(false)
      setFeedbackText('')
      setFeedbackSummary(null)
    } finally {
      setSubmittingFeedback(false)
    }
  }

  const handleSkipFeedback = async () => {
    setSubmittingFeedback(true)
    try {
      await submitFeedback(runId, '')
      setFeedbackRequested(false)
      setFeedbackText('')
      setFeedbackSummary(null)
    } finally {
      setSubmittingFeedback(false)
    }
  }

  const leftPrompt = diffLeft != null ? sortedIterations.find(i => i.iteration_num === diffLeft)?.prompt_template : null
  const rightPrompt = diffRight != null ? sortedIterations.find(i => i.iteration_num === diffRight)?.prompt_template : null

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <Link to="/" className="text-sm text-indigo-600 hover:text-indigo-700 mb-1 inline-block">&larr; Back</Link>
          <h1 className="text-2xl font-bold text-gray-900">{run.name}</h1>
          <div className="flex items-center gap-3 mt-2">
            <StatusBadge status={run.status} />
            {liveStatus && <span className="text-sm text-blue-600 animate-pulse">{liveStatus}</span>}
          </div>
        </div>
        {run.status === 'running' && (
          <button
            onClick={() => stopRun.mutateAsync(runId)}
            className="bg-red-100 text-red-700 px-4 py-2 rounded-lg hover:bg-red-200 text-sm font-medium"
          >
            Stop Run
          </button>
        )}
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4">
        {[
          { label: 'Best Score', value: run.best_score != null ? `${(run.best_score * 100).toFixed(1)}%` : '—' },
          { label: 'Iterations', value: run.total_iterations_completed },
          { label: 'Dataset', value: run.dataset_filename },
          { label: 'Target', value: `${(run.config.target_score * 100).toFixed(0)}%` },
        ].map((stat) => (
          <div key={stat.label} className="bg-white rounded-lg border p-4">
            <span className="text-xs text-gray-500">{stat.label}</span>
            <p className="text-lg font-semibold mt-1">{stat.value}</p>
          </div>
        ))}
      </div>

      {/* Feedback Panel */}
      {feedbackRequested && feedbackSummary && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-amber-800">Feedback Requested</h2>
            <span className="text-xs text-amber-600">Iteration {feedbackSummary.iteration}</span>
          </div>
          <div className="grid grid-cols-3 gap-3 text-sm">
            <div className="bg-white rounded p-2 text-center">
              <span className="text-xs text-gray-500">Avg Score</span>
              <p className="font-semibold">{(feedbackSummary.summary.avg_score * 100).toFixed(1)}%</p>
            </div>
            <div className="bg-white rounded p-2 text-center">
              <span className="text-xs text-gray-500">Min Score</span>
              <p className="font-semibold">{(feedbackSummary.summary.min_score * 100).toFixed(1)}%</p>
            </div>
            <div className="bg-white rounded p-2 text-center">
              <span className="text-xs text-gray-500">Max Score</span>
              <p className="font-semibold">{(feedbackSummary.summary.max_score * 100).toFixed(1)}%</p>
            </div>
          </div>
          {feedbackSummary.summary.failure_patterns.length > 0 && (
            <div>
              <h3 className="text-xs font-medium text-amber-700 mb-1">Failure Patterns</h3>
              <ul className="text-xs text-gray-700 list-disc list-inside">
                {feedbackSummary.summary.failure_patterns.map((p, i) => <li key={i}>{p}</li>)}
              </ul>
            </div>
          )}
          {feedbackSummary.summary.suggestions.length > 0 && (
            <div>
              <h3 className="text-xs font-medium text-amber-700 mb-1">Suggestions</h3>
              <ul className="text-xs text-gray-700 list-disc list-inside">
                {feedbackSummary.summary.suggestions.map((s, i) => <li key={i}>{s}</li>)}
              </ul>
            </div>
          )}
          <div>
            <label className="block text-xs font-medium text-amber-700 mb-1">Your Feedback (optional guidance for the improver)</label>
            <textarea
              value={feedbackText}
              onChange={(e) => setFeedbackText(e.target.value)}
              rows={3}
              className="w-full border border-amber-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-amber-500 focus:border-amber-500"
              placeholder="e.g., Focus on handling edge cases better, or try a different approach for the failing patterns..."
            />
          </div>
          <div className="flex gap-2">
            <button
              onClick={handleSubmitFeedback}
              disabled={submittingFeedback}
              className="bg-amber-600 text-white px-4 py-2 rounded-lg hover:bg-amber-700 disabled:opacity-50 text-sm font-medium"
            >
              {submittingFeedback ? 'Submitting...' : 'Submit & Continue'}
            </button>
            <button
              onClick={handleSkipFeedback}
              disabled={submittingFeedback}
              className="border border-amber-300 text-amber-700 px-4 py-2 rounded-lg hover:bg-amber-100 disabled:opacity-50 text-sm"
            >
              Skip
            </button>
          </div>
        </div>
      )}

      {/* Chart */}
      <div className="bg-white rounded-lg border p-4">
        <h2 className="text-lg font-semibold mb-4">Score Progression</h2>
        <ScoreChart iterations={sortedIterations} targetScore={run.config.target_score} />
      </div>

      {/* Best Prompt */}
      {run.best_prompt && (
        <div className="bg-white rounded-lg border p-4">
          <div className="flex items-center justify-between mb-2">
            <h2 className="text-lg font-semibold">Best Prompt</h2>
            <button onClick={handleCopyBest} className="text-sm text-indigo-600 hover:text-indigo-700">
              {copied ? 'Copied!' : 'Copy'}
            </button>
          </div>
          <pre className="bg-gray-50 border rounded-lg p-4 text-sm whitespace-pre-wrap">{run.best_prompt}</pre>
        </div>
      )}

      {/* Prompt Diff */}
      {sortedIterations.length >= 2 && (
        <div className="bg-white rounded-lg border p-4">
          <h2 className="text-lg font-semibold mb-3">Compare Prompts</h2>
          <div className="flex items-center gap-3 mb-4">
            <select value={diffLeft ?? ''} onChange={(e) => setDiffLeft(Number(e.target.value) || null)}
              className="border rounded-lg px-3 py-1.5 text-sm">
              <option value="">Select left...</option>
              <option value={0}>Initial Prompt</option>
              {sortedIterations.map((it) => (
                <option key={it.iteration_num} value={it.iteration_num}>Iteration {it.iteration_num}</option>
              ))}
            </select>
            <span className="text-gray-400">vs</span>
            <select value={diffRight ?? ''} onChange={(e) => setDiffRight(Number(e.target.value) || null)}
              className="border rounded-lg px-3 py-1.5 text-sm">
              <option value="">Select right...</option>
              <option value={0}>Initial Prompt</option>
              {sortedIterations.map((it) => (
                <option key={it.iteration_num} value={it.iteration_num}>Iteration {it.iteration_num}</option>
              ))}
            </select>
          </div>
          {leftPrompt != null && rightPrompt != null && (
            <PromptDiff
              left={diffLeft === 0 ? run.initial_prompt : (leftPrompt || '')}
              right={diffRight === 0 ? run.initial_prompt : (rightPrompt || '')}
              leftLabel={diffLeft === 0 ? 'Initial' : `Iteration ${diffLeft}`}
              rightLabel={diffRight === 0 ? 'Initial' : `Iteration ${diffRight}`}
            />
          )}
        </div>
      )}

      {/* Iterations */}
      <div className="bg-white rounded-lg border p-4">
        <h2 className="text-lg font-semibold mb-4">Iterations</h2>
        <div className="space-y-2">
          {sortedIterations.length === 0 ? (
            <p className="text-gray-400 text-sm">No iterations yet</p>
          ) : (
            sortedIterations.map((it) => (
              <Link
                key={it.id}
                to={`/runs/${runId}/iterations/${it.iteration_num}`}
                className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
              >
                <div className="flex items-center gap-4">
                  <span className="font-medium text-sm">#{it.iteration_num}</span>
                  <span className="text-sm text-gray-600">
                    Avg: {it.avg_score != null ? `${(it.avg_score * 100).toFixed(1)}%` : '—'}
                  </span>
                </div>
                <span className="text-xs text-gray-400">&rarr;</span>
              </Link>
            ))
          )}
        </div>
      </div>

      {/* Logs */}
      {logs && logs.length > 0 && (
        <div className="bg-white rounded-lg border p-4">
          <h2 className="text-lg font-semibold mb-4">Logs</h2>
          <LogViewer logs={logs} />
        </div>
      )}

      {/* Error */}
      {run.error_message && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <h3 className="text-red-800 font-medium text-sm">Error</h3>
          <p className="text-red-700 text-sm mt-1">{run.error_message}</p>
        </div>
      )}
    </div>
  )
}
