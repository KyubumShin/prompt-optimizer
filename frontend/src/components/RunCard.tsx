import { Link } from 'react-router-dom'
import type { Run } from '../types'
import StatusBadge from './StatusBadge'

export default function RunCard({ run, onDelete }: { run: Run; onDelete?: (id: number) => void }) {
  return (
    <Link
      to={`/runs/${run.id}`}
      className="block bg-white rounded-lg border border-gray-200 p-5 hover:shadow-md transition-shadow"
    >
      <div className="flex items-start justify-between mb-3">
        <h3 className="font-semibold text-gray-900 truncate mr-3">{run.name}</h3>
        <div className="flex items-center gap-2 shrink-0">
          <StatusBadge status={run.status} />
          {onDelete && (
            <button
              onClick={(e) => {
                e.preventDefault()
                e.stopPropagation()
                if (window.confirm(`Delete run "${run.name}"?`)) {
                  onDelete(run.id)
                }
              }}
              className="text-gray-400 hover:text-red-500 hover:bg-red-50 rounded p-1 text-sm leading-none transition-colors"
              title="Delete run"
            >
              ×
            </button>
          )}
        </div>
      </div>
      <div className="grid grid-cols-3 gap-4 text-sm">
        <div>
          <span className="text-gray-500">Best Score</span>
          <p className="font-medium text-lg">
            {run.best_score != null ? `${(run.best_score * 100).toFixed(1)}%` : '—'}
          </p>
        </div>
        <div>
          <span className="text-gray-500">Iterations</span>
          <p className="font-medium text-lg">{run.total_iterations_completed}</p>
        </div>
        <div>
          <span className="text-gray-500">Dataset</span>
          <p className="font-medium truncate">{run.dataset_filename}</p>
        </div>
      </div>
      <p className="mt-3 text-xs text-gray-400">
        {new Date(run.created_at).toLocaleString()}
      </p>
    </Link>
  )
}
