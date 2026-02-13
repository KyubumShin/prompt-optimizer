from __future__ import annotations

import asyncio
import json
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import Run
from ..services.event_manager import event_manager

router = APIRouter(prefix="/api/runs", tags=["stream"])

SSE_KEEPALIVE_TIMEOUT_SECONDS = 30.0


@router.get("/{run_id}/stream")
async def stream_run(run_id: int, db: AsyncSession = Depends(get_db)):
    run = await db.get(Run, run_id)
    if not run:
        raise HTTPException(404, "Run not found")

    queue = event_manager.subscribe(run_id)

    async def event_generator():
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=SSE_KEEPALIVE_TIMEOUT_SECONDS)
                    yield f"event: {event.event}\ndata: {json.dumps(event.data)}\n\n"

                    # Terminal events
                    if event.event in ("completed", "converged", "failed", "stopped"):
                        break
                except asyncio.TimeoutError:
                    # Keepalive comment
                    yield ": keepalive\n\n"
        finally:
            event_manager.unsubscribe(run_id, queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
