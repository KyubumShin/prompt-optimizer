from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

@dataclass
class SSEEvent:
    event: str
    data: dict

class EventManager:
    """Per-run SSE event queue with multi-subscriber support."""

    def __init__(self):
        self._subscribers: dict[int, list[asyncio.Queue]] = {}  # run_id -> [queues]

    def subscribe(self, run_id: int) -> asyncio.Queue:
        if run_id not in self._subscribers:
            self._subscribers[run_id] = []
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers[run_id].append(queue)
        return queue

    def unsubscribe(self, run_id: int, queue: asyncio.Queue):
        if run_id in self._subscribers:
            try:
                self._subscribers[run_id].remove(queue)
            except ValueError:
                pass
            if not self._subscribers[run_id]:
                del self._subscribers[run_id]

    async def emit(self, run_id: int, event: str, data: dict):
        if run_id not in self._subscribers:
            return
        for queue in self._subscribers[run_id]:
            await queue.put(SSEEvent(event=event, data=data))

    async def emit_stage_start(self, run_id: int, stage: str, iteration: int):
        await self.emit(run_id, "stage_start", {"stage": stage, "iteration": iteration})

    async def emit_test_progress(self, run_id: int, completed: int, total: int):
        await self.emit(run_id, "test_progress", {"completed": completed, "total": total})

    async def emit_iteration_complete(self, run_id: int, iteration: int, avg_score: float, best_score: float):
        await self.emit(run_id, "iteration_complete", {"iteration": iteration, "avg_score": avg_score, "best_score": best_score})

    async def emit_completed(self, run_id: int, best_score: float, total_iterations: int):
        await self.emit(run_id, "completed", {"best_score": best_score, "total_iterations": total_iterations})

    async def emit_converged(self, run_id: int, reason: str, best_score: float):
        await self.emit(run_id, "converged", {"reason": reason, "best_score": best_score})

    async def emit_failed(self, run_id: int, error: str):
        await self.emit(run_id, "failed", {"error": error})

    async def emit_stopped(self, run_id: int):
        await self.emit(run_id, "stopped", {})

    async def emit_feedback_requested(self, run_id: int, iteration: int, summary_data: dict):
        await self.emit(run_id, "feedback_requested", {"iteration": iteration, "summary": summary_data})

# Global singleton
event_manager = EventManager()
