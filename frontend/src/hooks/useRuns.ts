import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import * as api from '../lib/api'

export function useRuns() {
  return useQuery({
    queryKey: ['runs'],
    queryFn: api.listRuns,
    refetchInterval: 5000,
  })
}

export function useRun(id: number) {
  return useQuery({
    queryKey: ['runs', id],
    queryFn: () => api.getRun(id),
    refetchInterval: (query) => {
      const status = query.state.data?.status
      return status === 'running' || status === 'pending' ? 3000 : false
    },
  })
}

export function useIterations(runId: number) {
  return useQuery({
    queryKey: ['runs', runId, 'iterations'],
    queryFn: () => api.getIterations(runId),
  })
}

export function useIteration(runId: number, iterNum: number) {
  return useQuery({
    queryKey: ['runs', runId, 'iterations', iterNum],
    queryFn: () => api.getIteration(runId, iterNum),
  })
}

export function useLogs(runId: number, stage?: string, level?: string) {
  return useQuery({
    queryKey: ['runs', runId, 'logs', stage, level],
    queryFn: () => api.getLogs(runId, stage, level),
    refetchInterval: 5000,
  })
}

export function useCreateRun() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: api.createRun,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['runs'] }),
  })
}

export function useStopRun() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: api.stopRun,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['runs'] }),
  })
}

export function useDeleteRun() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: api.deleteRun,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['runs'] }),
  })
}
