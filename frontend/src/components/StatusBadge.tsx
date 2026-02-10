import clsx from 'clsx'

const statusStyles: Record<string, string> = {
  pending: 'bg-yellow-100 text-yellow-800',
  running: 'bg-blue-100 text-blue-800',
  completed: 'bg-green-100 text-green-800',
  failed: 'bg-red-100 text-red-800',
  stopped: 'bg-gray-100 text-gray-800',
}

export default function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={clsx(
        'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium capitalize',
        statusStyles[status] || 'bg-gray-100 text-gray-800'
      )}
    >
      {status === 'running' && (
        <span className="w-1.5 h-1.5 bg-blue-500 rounded-full mr-1.5 animate-pulse" />
      )}
      {status}
    </span>
  )
}
