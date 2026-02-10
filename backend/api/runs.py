import asyncio
import json
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload

from ..database import get_db
from ..models import Run, Iteration, TestResult, Log
from ..schemas import RunCreate, RunResponse, RunDetailResponse, IterationResponse, IterationDetailResponse, TestResultResponse, LogResponse, RunConfig
from ..config import Settings, get_settings
from ..services.csv_loader import parse_csv, validate_prompt_columns
from ..services.pipeline import run_pipeline, request_stop

router = APIRouter(prefix="/api/runs", tags=["runs"])

@router.post("", response_model=RunResponse)
async def create_run(
    name: str = Form(...),
    initial_prompt: str = Form(...),
    config_json: str = Form("{}"),
    expected_column: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    # Parse CSV
    content = await file.read()
    try:
        dataset = parse_csv(content, file.filename or "upload.csv")
    except ValueError as e:
        raise HTTPException(400, str(e))

    # Parse config
    try:
        config_data = json.loads(config_json)
        config = RunConfig(**config_data)
    except Exception as e:
        raise HTTPException(400, f"Invalid config: {e}")

    # Validate expected column exists
    if expected_column not in dataset.columns:
        raise HTTPException(400, f"Expected column '{expected_column}' not found in CSV. Available: {dataset.columns}")

    # Validate prompt placeholders
    input_columns = [c for c in dataset.columns if c != expected_column]
    missing = validate_prompt_columns(initial_prompt, input_columns)
    if missing:
        raise HTTPException(400, f"Prompt references columns not in CSV: {missing}. Available: {input_columns}")

    # Create run
    run = Run(
        name=name,
        initial_prompt=initial_prompt,
        config=config.model_dump(),
        dataset_filename=dataset.filename,
        dataset_columns=dataset.columns,
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)

    # Launch pipeline as background task
    from ..database import async_session_factory
    asyncio.create_task(
        run_pipeline(run.id, async_session_factory, settings, dataset.rows, expected_column, input_columns)
    )

    return run

@router.get("", response_model=List[RunResponse])
async def list_runs(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Run).order_by(desc(Run.created_at)))
    return result.scalars().all()

@router.get("/{run_id}", response_model=RunDetailResponse)
async def get_run(run_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Run).where(Run.id == run_id).options(selectinload(Run.iterations))
    )
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(404, "Run not found")
    return run

@router.get("/{run_id}/iterations", response_model=List[IterationResponse])
async def list_iterations(run_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Iteration).where(Iteration.run_id == run_id).order_by(Iteration.iteration_num)
    )
    return result.scalars().all()

@router.get("/{run_id}/iterations/{iter_num}", response_model=IterationDetailResponse)
async def get_iteration(run_id: int, iter_num: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Iteration)
        .where(Iteration.run_id == run_id, Iteration.iteration_num == iter_num)
        .options(selectinload(Iteration.test_results))
    )
    iteration = result.scalar_one_or_none()
    if not iteration:
        raise HTTPException(404, "Iteration not found")
    return iteration

@router.get("/{run_id}/logs", response_model=List[LogResponse])
async def get_logs(
    run_id: int,
    stage: Optional[str] = None,
    level: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(Log).where(Log.run_id == run_id)
    if stage:
        query = query.where(Log.stage == stage)
    if level:
        query = query.where(Log.level == level)
    query = query.order_by(Log.created_at)
    result = await db.execute(query)
    return result.scalars().all()

@router.post("/{run_id}/stop")
async def stop_run(run_id: int, db: AsyncSession = Depends(get_db)):
    run = await db.get(Run, run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    if run.status != "running":
        raise HTTPException(400, f"Run is not running (status: {run.status})")
    request_stop(run_id)
    return {"message": "Stop requested"}

@router.delete("/{run_id}")
async def delete_run(run_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Run).where(Run.id == run_id)
        .options(selectinload(Run.iterations).selectinload(Iteration.test_results))
        .options(selectinload(Run.logs))
    )
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(404, "Run not found")
    if run.status == "running":
        request_stop(run_id)
        import asyncio
        await asyncio.sleep(1)
    await db.delete(run)
    await db.commit()
    return {"message": "Run deleted"}
