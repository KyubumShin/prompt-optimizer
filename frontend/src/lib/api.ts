import axios from 'axios'
import type { Run, RunDetail, Iteration, IterationDetail, LogEntry } from '../types'

const client = axios.create({ baseURL: '/api' })

export async function createRun(formData: FormData): Promise<Run> {
  const { data } = await client.post('/runs', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export async function listRuns(): Promise<Run[]> {
  const { data } = await client.get('/runs')
  return data
}

export async function getRun(id: number): Promise<RunDetail> {
  const { data } = await client.get(`/runs/${id}`)
  return data
}

export async function getIterations(runId: number): Promise<Iteration[]> {
  const { data } = await client.get(`/runs/${runId}/iterations`)
  return data
}

export async function getIteration(runId: number, iterNum: number): Promise<IterationDetail> {
  const { data } = await client.get(`/runs/${runId}/iterations/${iterNum}`)
  return data
}

export async function getLogs(runId: number, stage?: string, level?: string): Promise<LogEntry[]> {
  const params: Record<string, string> = {}
  if (stage) params.stage = stage
  if (level) params.level = level
  const { data } = await client.get(`/runs/${runId}/logs`, { params })
  return data
}

export async function stopRun(id: number): Promise<void> {
  await client.post(`/runs/${id}/stop`)
}

export async function deleteRun(id: number): Promise<void> {
  await client.delete(`/runs/${id}`)
}
