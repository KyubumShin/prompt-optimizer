import { Link } from 'react-router-dom'
import { useRuns } from '../hooks/useRuns'
import RunCard from '../components/RunCard'

export default function Dashboard() {
  const { data: runs, isLoading } = useRuns()

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Optimization Runs</h1>
        <Link
          to="/new"
          className="bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700 transition-colors text-sm font-medium"
        >
          New Run
        </Link>
      </div>

      {isLoading ? (
        <div className="text-center py-12 text-gray-400">Loading...</div>
      ) : !runs || runs.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-gray-500 mb-4">No optimization runs yet</p>
          <Link
            to="/new"
            className="text-indigo-600 hover:text-indigo-700 font-medium"
          >
            Create your first run
          </Link>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {runs.map((run) => (
            <RunCard key={run.id} run={run} />
          ))}
        </div>
      )}
    </div>
  )
}
