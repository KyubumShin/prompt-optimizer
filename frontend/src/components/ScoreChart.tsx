import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts'
import type { Iteration } from '../types'

interface Props {
  iterations: Iteration[]
  targetScore?: number
}

export default function ScoreChart({ iterations, targetScore }: Props) {
  const data = iterations
    .filter((it) => it.avg_score != null)
    .map((it) => ({
      iteration: it.iteration_num,
      avg: Number((it.avg_score! * 100).toFixed(1)),
      min: Number((it.min_score! * 100).toFixed(1)),
      max: Number((it.max_score! * 100).toFixed(1)),
    }))

  if (data.length === 0) {
    return <div className="text-gray-400 text-center py-8">No iteration data yet</div>
  }

  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={data} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
        <XAxis dataKey="iteration" label={{ value: 'Iteration', position: 'insideBottom', offset: -2 }} />
        <YAxis domain={[0, 100]} label={{ value: 'Score %', angle: -90, position: 'insideLeft' }} />
        <Tooltip formatter={(value: number) => `${value}%`} />
        {targetScore && (
          <ReferenceLine y={targetScore * 100} stroke="#10b981" strokeDasharray="5 5" label="Target" />
        )}
        <Line type="monotone" dataKey="avg" stroke="#6366f1" strokeWidth={2} name="Average" dot={{ r: 4 }} />
        <Line type="monotone" dataKey="min" stroke="#f59e0b" strokeWidth={1} strokeDasharray="4 4" name="Min" dot={false} />
        <Line type="monotone" dataKey="max" stroke="#10b981" strokeWidth={1} strokeDasharray="4 4" name="Max" dot={false} />
      </LineChart>
    </ResponsiveContainer>
  )
}
