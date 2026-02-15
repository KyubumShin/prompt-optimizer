import { useParams, Link } from 'react-router-dom'
import { useIteration } from '../hooks/useRuns'
import TestResultTable from '../components/TestResultTable'

export default function IterationDetail() {
  const { id, num } = useParams<{ id: string; num: string }>()
  const runId = Number(id)
  const iterNum = Number(num)
  const { data: iteration, isLoading } = useIteration(runId, iterNum)

  if (isLoading) return <div className="text-center py-12 text-gray-400">Loading...</div>
  if (!iteration) return <div className="text-center py-12 text-gray-400">Iteration not found</div>

  const scores = iteration.test_results?.map((r) => r.score).filter((s): s is number => s != null) || []
  const avgScore = scores.length ? scores.reduce((a, b) => a + b, 0) / scores.length : null

  return (
    <div className="space-y-6">
      <div>
        <Link to={`/runs/${runId}`} className="text-sm text-indigo-600 hover:text-indigo-700 mb-1 inline-block">
          &larr; Back to Run
        </Link>
        <h1 className="text-2xl font-bold text-gray-900">Iteration #{iterNum}</h1>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4">
        {[
          { label: 'Average', value: iteration.avg_score != null ? `${(iteration.avg_score * 100).toFixed(1)}%` : '—' },
          { label: 'Min', value: iteration.min_score != null ? `${(iteration.min_score * 100).toFixed(1)}%` : '—' },
          { label: 'Max', value: iteration.max_score != null ? `${(iteration.max_score * 100).toFixed(1)}%` : '—' },
          { label: 'Test Cases', value: iteration.test_results?.length || 0 },
        ].map((stat) => (
          <div key={stat.label} className="bg-white rounded-lg border p-4">
            <span className="text-xs text-gray-500">{stat.label}</span>
            <p className="text-lg font-semibold mt-1">{stat.value}</p>
          </div>
        ))}
      </div>

      {/* Prompt */}
      <div className="bg-white rounded-lg border p-4">
        <h2 className="text-lg font-semibold mb-2">Prompt Template</h2>
        <pre className="bg-gray-50 border rounded-lg p-4 text-sm whitespace-pre-wrap">
          {iteration.prompt_template}
        </pre>
      </div>

      {/* Summary */}
      {iteration.summary && (
        <div className="bg-white rounded-lg border p-4">
          <h2 className="text-lg font-semibold mb-2">Analysis Summary</h2>
          <p className="text-sm text-gray-700">{iteration.summary}</p>
        </div>
      )}

      {/* Improvement */}
      {iteration.improvement_reasoning && (
        <div className="bg-white rounded-lg border p-4">
          <h2 className="text-lg font-semibold mb-2">Improvement Reasoning</h2>
          <p className="text-sm text-gray-700">{iteration.improvement_reasoning}</p>
        </div>
      )}

      {/* Improver Prompt (Step 4) */}
      {iteration.improver_prompt && (
        <details className="bg-white rounded-lg border">
          <summary className="p-4 cursor-pointer select-none hover:bg-gray-50">
            <h2 className="text-lg font-semibold inline">Improver Prompt (Step 4)</h2>
            <span className="text-sm text-gray-500 ml-2">Click to expand</span>
          </summary>
          <div className="px-4 pb-4">
            <pre className="bg-gray-50 border rounded-lg p-4 text-sm whitespace-pre-wrap max-h-96 overflow-y-auto">
              {iteration.improver_prompt}
            </pre>
          </div>
        </details>
      )}

      {/* Test Results */}
      <div className="bg-white rounded-lg border p-4">
        <h2 className="text-lg font-semibold mb-4">Test Results</h2>
        {iteration.test_results && iteration.test_results.length > 0 ? (
          <TestResultTable results={iteration.test_results} />
        ) : (
          <p className="text-gray-400 text-sm">No test results</p>
        )}
      </div>
    </div>
  )
}
