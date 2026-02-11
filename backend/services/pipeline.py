from __future__ import annotations

import asyncio
import json
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..config import Settings
from ..models import Run, Iteration, TestResult, Log
from .llm_client import LLMClient, create_llm_client
from .tester import run_tests
from .judge import judge_results
from .summarizer import summarize_results
from .improver import improve_prompt
from .event_manager import event_manager

logger = logging.getLogger(__name__)

# Track cancellation flags per run
_cancel_flags: dict[int, bool] = {}

def request_stop(run_id: int):
    _cancel_flags[run_id] = True

def is_cancelled(run_id: int) -> bool:
    return _cancel_flags.get(run_id, False)

async def _add_log(session: AsyncSession, run_id: int, stage: str, level: str, message: str, iteration_id: int | None = None, data: dict | None = None):
    log = Log(run_id=run_id, iteration_id=iteration_id, stage=stage, level=level, message=message, data=data)
    session.add(log)
    await session.flush()


def _resolve_client(settings: Settings, config: dict, stage: str) -> tuple:
    """Resolve provider + model + client for a pipeline stage.

    Returns (client, model_name).
    Falls back to legacy single-provider config for backward compatibility.
    """
    if stage == "test":
        provider_id = config.get("model_provider")
        model_name = config.get("model") or settings.OPENAI_MODEL
    elif stage == "judge":
        provider_id = config.get("judge_provider")
        model_name = config.get("judge_model") or settings.JUDGE_MODEL
    elif stage == "improver":
        provider_id = config.get("improver_provider")
        model_name = config.get("improver_model") or settings.IMPROVER_MODEL
    else:
        provider_id = None
        model_name = config.get("model") or settings.OPENAI_MODEL

    # If a provider is specified, build a client for it
    if provider_id:
        providers = settings.get_providers()
        provider = next((p for p in providers if p["id"] == provider_id), None)
        if provider and provider["configured"] and provider["api_key"]:
            client = create_llm_client(provider["provider_type"], provider["api_key"], provider["base_url"])
            return client, model_name

    # Fallback: use legacy single-provider config
    client = LLMClient(api_key=settings.OPENAI_API_KEY, base_url=settings.OPENAI_BASE_URL)
    return client, model_name


async def run_pipeline(run_id: int, session_factory, settings: Settings, test_cases: list[dict], expected_col: str, input_columns: list[str]):
    """Main pipeline orchestrator. Runs as an asyncio task."""
    _cancel_flags[run_id] = False

    async with session_factory() as session:
        try:
            # Get the run
            run = await session.get(Run, run_id)
            if not run:
                return

            run.status = "running"
            await session.commit()

            config = run.config or {}

            # Resolve per-stage clients
            test_client, model = _resolve_client(settings, config, "test")
            judge_client, judge_model = _resolve_client(settings, config, "judge")
            improver_client, improver_model = _resolve_client(settings, config, "improver")

            max_iterations = config.get("max_iterations", settings.DEFAULT_MAX_ITERATIONS)
            target_score = config.get("target_score", settings.DEFAULT_TARGET_SCORE)
            temperature = config.get("temperature", settings.DEFAULT_TEMPERATURE)
            concurrency = config.get("concurrency", settings.DEFAULT_CONCURRENCY)
            custom_judge_prompt = config.get("judge_prompt")
            convergence_threshold = config.get("convergence_threshold", settings.CONVERGENCE_THRESHOLD)
            convergence_patience = config.get("convergence_patience", settings.CONVERGENCE_PATIENCE)

            current_prompt = run.initial_prompt
            best_score = 0.0
            best_prompt = current_prompt
            prev_scores = []

            await _add_log(session, run_id, "system", "info", f"Pipeline started. Max iterations: {max_iterations}, target: {target_score}")
            await session.commit()

            for iter_num in range(1, max_iterations + 1):
                if is_cancelled(run_id):
                    run.status = "stopped"
                    await _add_log(session, run_id, "system", "info", "Pipeline stopped by user")
                    await event_manager.emit_stopped(run_id)
                    await session.commit()
                    return

                # Create iteration record
                iteration = Iteration(run_id=run_id, iteration_num=iter_num, prompt_template=current_prompt)
                session.add(iteration)
                await session.flush()

                # Stage 1: Test
                await event_manager.emit_stage_start(run_id, "test", iter_num)
                await _add_log(session, run_id, "test", "info", f"Iteration {iter_num}: Running tests on {len(test_cases)} cases", iteration.id)

                async def on_progress(completed, total):
                    await event_manager.emit_test_progress(run_id, completed, total)

                test_results_data = await run_tests(
                    test_client, current_prompt, test_cases, expected_col,
                    model=model, temperature=temperature, concurrency=concurrency,
                    on_progress=on_progress,
                )

                if is_cancelled(run_id):
                    run.status = "stopped"
                    await event_manager.emit_stopped(run_id)
                    await session.commit()
                    return

                # Stage 2: Judge
                await event_manager.emit_stage_start(run_id, "judge", iter_num)
                await _add_log(session, run_id, "judge", "info", f"Iteration {iter_num}: Judging results", iteration.id)

                judge_results_data = await judge_results(
                    judge_client, test_results_data, judge_model=judge_model,
                    custom_judge_prompt=custom_judge_prompt, concurrency=concurrency,
                )

                # Save test results to DB
                for test, judge in zip(test_results_data, judge_results_data):
                    tr = TestResult(
                        iteration_id=iteration.id,
                        test_case_index=test["index"],
                        input_data=test["input_data"],
                        expected_output=test["expected"],
                        actual_output=test.get("actual"),
                        score=judge["score"],
                        judge_reasoning=judge["reasoning"],
                    )
                    session.add(tr)

                if is_cancelled(run_id):
                    run.status = "stopped"
                    await event_manager.emit_stopped(run_id)
                    await session.commit()
                    return

                # Stage 3: Summarize
                await event_manager.emit_stage_start(run_id, "summarize", iter_num)
                await _add_log(session, run_id, "summarize", "info", f"Iteration {iter_num}: Summarizing results", iteration.id)

                summary = await summarize_results(improver_client, current_prompt, test_results_data, judge_results_data, model=improver_model)

                # Update iteration with scores
                iteration.avg_score = summary["avg_score"]
                iteration.min_score = summary["min_score"]
                iteration.max_score = summary["max_score"]
                iteration.summary = summary.get("summary", "")

                # Track best
                if summary["avg_score"] > best_score:
                    best_score = summary["avg_score"]
                    best_prompt = current_prompt

                await _add_log(session, run_id, "summarize", "info",
                    f"Iteration {iter_num}: avg={summary['avg_score']:.3f}, min={summary['min_score']:.3f}, max={summary['max_score']:.3f}",
                    iteration.id, {"summary": summary})

                await event_manager.emit_iteration_complete(run_id, iter_num, summary["avg_score"], best_score)

                # Check convergence
                if summary["avg_score"] >= target_score:
                    best_prompt = current_prompt
                    best_score = summary["avg_score"]
                    iteration.improvement_reasoning = "Target score reached"
                    run.status = "completed"
                    run.best_prompt = best_prompt
                    run.best_score = best_score
                    run.total_iterations_completed = iter_num
                    await _add_log(session, run_id, "system", "info", f"Converged: target score {target_score} reached with {summary['avg_score']:.3f}", iteration.id)
                    await event_manager.emit_converged(run_id, "target_score_reached", best_score)
                    await session.commit()
                    return

                # Check stagnation
                prev_scores.append(summary["avg_score"])
                if len(prev_scores) >= convergence_patience + 1:
                    recent = prev_scores[-convergence_patience:]
                    if all(abs(recent[i] - recent[i-1]) < convergence_threshold for i in range(1, len(recent))):
                        run.status = "completed"
                        run.best_prompt = best_prompt
                        run.best_score = best_score
                        run.total_iterations_completed = iter_num
                        iteration.improvement_reasoning = "Convergence: score stagnated"
                        await _add_log(session, run_id, "system", "info", f"Converged: improvement below threshold for {convergence_patience} rounds", iteration.id)
                        await event_manager.emit_converged(run_id, "stagnation", best_score)
                        await session.commit()
                        return

                if is_cancelled(run_id):
                    run.status = "stopped"
                    await event_manager.emit_stopped(run_id)
                    await session.commit()
                    return

                # Stage 4: Improve (skip on last iteration)
                if iter_num < max_iterations:
                    await event_manager.emit_stage_start(run_id, "improve", iter_num)
                    await _add_log(session, run_id, "improve", "info", f"Iteration {iter_num}: Generating improved prompt", iteration.id)

                    improvement = await improve_prompt(
                        improver_client, current_prompt, summary,
                        available_columns=input_columns, model=improver_model, target_score=target_score,
                    )

                    iteration.improvement_reasoning = improvement["reasoning"]
                    current_prompt = improvement["improved_prompt"]

                    await _add_log(session, run_id, "improve", "info",
                        f"Iteration {iter_num}: Prompt improved", iteration.id,
                        {"reasoning": improvement["reasoning"]})

                run.total_iterations_completed = iter_num
                await session.commit()

            # Max iterations reached
            run.status = "completed"
            run.best_prompt = best_prompt
            run.best_score = best_score
            await _add_log(session, run_id, "system", "info", f"Completed: max iterations ({max_iterations}) reached. Best score: {best_score:.3f}")
            await event_manager.emit_completed(run_id, best_score, max_iterations)
            await session.commit()

        except Exception as e:
            logger.exception(f"Pipeline error for run {run_id}")
            try:
                run = await session.get(Run, run_id)
                if run:
                    run.status = "failed"
                    run.error_message = str(e)
                    await _add_log(session, run_id, "system", "error", f"Pipeline failed: {e}")
                    await session.commit()
                await event_manager.emit_failed(run_id, str(e))
            except Exception:
                logger.exception("Failed to update run status after error")
        finally:
            _cancel_flags.pop(run_id, None)
