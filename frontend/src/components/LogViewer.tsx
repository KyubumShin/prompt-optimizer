import { useState } from 'react'
import clsx from 'clsx'
import type { LogEntry } from '../types'

const stages = ['all', 'test', 'judge', 'summarize', 'improve', 'system']
const levels = ['all', 'info', 'warn', 'error']

const levelStyles: Record<string, string> = {
  info: 'text-blue-600',
  warn: 'text-yellow-600',
  error: 'text-red-600',
}

export default function LogViewer({ logs }: { logs: LogEntry[] }) {
  const [stageFilter, setStageFilter] = useState('all')
  const [levelFilter, setLevelFilter] = useState('all')

  const filtered = logs.filter((log) => {
    if (stageFilter !== 'all' && log.stage !== stageFilter) return false
    if (levelFilter !== 'all' && log.level !== levelFilter) return false
    return true
  })

  return (
    <div>
      <div className="flex gap-3 mb-4">
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500">Stage:</span>
          {stages.map((s) => (
            <button
              key={s}
              onClick={() => setStageFilter(s)}
              className={clsx(
                'px-2 py-1 text-xs rounded',
                stageFilter === s
                  ? 'bg-indigo-100 text-indigo-700'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              )}
            >
              {s}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500">Level:</span>
          {levels.map((l) => (
            <button
              key={l}
              onClick={() => setLevelFilter(l)}
              className={clsx(
                'px-2 py-1 text-xs rounded',
                levelFilter === l
                  ? 'bg-indigo-100 text-indigo-700'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              )}
            >
              {l}
            </button>
          ))}
        </div>
      </div>
      <div className="bg-gray-900 rounded-lg p-4 max-h-96 overflow-y-auto font-mono text-xs">
        {filtered.length === 0 ? (
          <p className="text-gray-500">No logs matching filters</p>
        ) : (
          filtered.map((log) => (
            <div key={log.id} className="flex gap-2 py-0.5">
              <span className="text-gray-500 flex-shrink-0">
                {new Date(log.created_at).toLocaleTimeString()}
              </span>
              <span className="text-gray-400 flex-shrink-0 w-16">[{log.stage}]</span>
              <span className={clsx('flex-shrink-0 w-10', levelStyles[log.level] || 'text-gray-400')}>
                {log.level}
              </span>
              <span className="text-gray-200">{log.message}</span>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
