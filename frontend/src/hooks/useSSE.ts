import { useEffect, useRef, useCallback } from 'react'
import type { SSEEvent } from '../types'

export function useSSE(
  runId: number | null,
  onEvent: (event: SSEEvent) => void,
  enabled: boolean = true,
) {
  const eventSourceRef = useRef<EventSource | null>(null)
  const onEventRef = useRef(onEvent)
  onEventRef.current = onEvent

  const connect = useCallback(() => {
    if (!runId || !enabled) return

    const url = `/api/runs/${runId}/stream`
    const es = new EventSource(url)
    eventSourceRef.current = es

    const eventTypes = [
      'stage_start', 'test_progress', 'iteration_complete',
      'converged', 'completed', 'failed', 'stopped',
    ]

    for (const type of eventTypes) {
      es.addEventListener(type, (e: MessageEvent) => {
        try {
          const data = JSON.parse(e.data)
          onEventRef.current({ event: type, data })
        } catch {
          // ignore parse errors
        }
      })
    }

    es.onerror = () => {
      es.close()
      // Reconnect after 3s
      setTimeout(() => connect(), 3000)
    }

    return () => {
      es.close()
    }
  }, [runId, enabled])

  useEffect(() => {
    const cleanup = connect()
    return () => {
      cleanup?.()
      eventSourceRef.current?.close()
    }
  }, [connect])
}
