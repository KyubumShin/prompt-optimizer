import { useState, Fragment } from 'react'
import clsx from 'clsx'
import type { TestResult } from '../types'

function scoreColor(score: number | null): string {
  if (score == null) return 'text-gray-400'
  if (score >= 0.8) return 'text-green-600'
  if (score >= 0.5) return 'text-yellow-600'
  return 'text-red-600'
}

function scoreBg(score: number | null): string {
  if (score == null) return 'bg-gray-50'
  if (score >= 0.8) return 'bg-green-50'
  if (score >= 0.5) return 'bg-yellow-50'
  return 'bg-red-50'
}

function isImageUrl(value: string): boolean {
  if (!value) return false
  const v = value.trim().toLowerCase()
  return /^https?:\/\/.+\.(png|jpg|jpeg|gif|webp)/i.test(v)
}

function ImageThumbnail({ src }: { src: string }) {
  const [showModal, setShowModal] = useState(false)
  return (
    <>
      <img
        src={src}
        alt=""
        className="w-10 h-10 object-cover rounded border cursor-pointer hover:opacity-80 inline-block"
        onClick={() => setShowModal(true)}
        onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }}
      />
      {showModal && (
        <div
          className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
          onClick={() => setShowModal(false)}
        >
          <div className="max-w-3xl max-h-[80vh] p-2 bg-white rounded-lg" onClick={(e) => e.stopPropagation()}>
            <img src={src} alt="" className="max-w-full max-h-[75vh] object-contain" />
            <div className="text-center mt-2">
              <a href={src} target="_blank" rel="noopener noreferrer" className="text-xs text-indigo-600 hover:underline">Open in new tab</a>
              <button onClick={() => setShowModal(false)} className="ml-4 text-xs text-gray-500 hover:text-gray-700">Close</button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}

export default function TestResultTable({ results, imageColumns }: { results: TestResult[]; imageColumns?: string[] }) {
  const [expanded, setExpanded] = useState<Set<number>>(new Set())

  const toggle = (id: number) => {
    setExpanded((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-200 text-left">
            <th className="py-2 pr-3 font-medium text-gray-500">#</th>
            <th className="py-2 pr-3 font-medium text-gray-500">Input</th>
            <th className="py-2 pr-3 font-medium text-gray-500">Expected</th>
            <th className="py-2 pr-3 font-medium text-gray-500">Actual</th>
            <th className="py-2 pr-3 font-medium text-gray-500">Score</th>
            <th className="py-2 font-medium text-gray-500"></th>
          </tr>
        </thead>
        <tbody>
          {results.map((r) => (
            <Fragment key={r.id}>
              <tr className={clsx('border-b border-gray-100', scoreBg(r.score))}>
                <td className="py-2 pr-3">{r.test_case_index + 1}</td>
                <td className="py-2 pr-3 max-w-[200px]">
                  <div className="flex items-center gap-1">
                    {imageColumns && imageColumns.length > 0 && imageColumns.map((col) => {
                      const val = r.input_data[col]
                      return val && isImageUrl(val) ? <ImageThumbnail key={col} src={val} /> : null
                    })}
                    <span className="truncate" title={JSON.stringify(r.input_data)}>
                      {Object.entries(r.input_data)
                        .filter(([k]) => !imageColumns?.includes(k))
                        .map(([, v]) => v)
                        .join(', ')}
                    </span>
                  </div>
                </td>
                <td className="py-2 pr-3 max-w-[200px] truncate" title={r.expected_output}>
                  {r.expected_output}
                </td>
                <td className="py-2 pr-3 max-w-[200px] truncate" title={r.actual_output || ''}>
                  {r.actual_output || '—'}
                </td>
                <td className={clsx('py-2 pr-3 font-medium', scoreColor(r.score))}>
                  {r.score != null ? `${(r.score * 100).toFixed(0)}%` : '—'}
                </td>
                <td className="py-2">
                  <button
                    onClick={() => toggle(r.id)}
                    className="text-indigo-600 hover:text-indigo-800 text-xs"
                  >
                    {expanded.has(r.id) ? 'Hide' : 'Details'}
                  </button>
                </td>
              </tr>
              {expanded.has(r.id) && (
                <tr>
                  <td colSpan={6} className="py-3 px-4 bg-gray-50">
                    <div className="space-y-2">
                      <div>
                        <span className="font-medium text-gray-500 text-xs">Input Data:</span>
                        {imageColumns && imageColumns.length > 0 && (
                          <div className="flex gap-2 mt-1 mb-1">
                            {imageColumns.map((col) => {
                              const val = r.input_data[col]
                              return val && isImageUrl(val) ? (
                                <div key={col} className="text-center">
                                  <ImageThumbnail src={val} />
                                  <span className="text-xs text-gray-400 block">{col}</span>
                                </div>
                              ) : null
                            })}
                          </div>
                        )}
                        <pre className="text-xs mt-1 bg-white p-2 rounded border">
                          {JSON.stringify(r.input_data, null, 2)}
                        </pre>
                      </div>
                      <div>
                        <span className="font-medium text-gray-500 text-xs">Expected:</span>
                        <pre className="text-xs mt-1 bg-white p-2 rounded border whitespace-pre-wrap">
                          {r.expected_output}
                        </pre>
                      </div>
                      <div>
                        <span className="font-medium text-gray-500 text-xs">Actual:</span>
                        <pre className="text-xs mt-1 bg-white p-2 rounded border whitespace-pre-wrap">
                          {r.actual_output || 'No output'}
                        </pre>
                      </div>
                      <div>
                        <span className="font-medium text-gray-500 text-xs">Judge Reasoning:</span>
                        <p className="text-xs mt-1 bg-white p-2 rounded border">
                          {r.judge_reasoning || 'No reasoning'}
                        </p>
                      </div>
                    </div>
                  </td>
                </tr>
              )}
            </Fragment>
          ))}
        </tbody>
      </table>
    </div>
  )
}
