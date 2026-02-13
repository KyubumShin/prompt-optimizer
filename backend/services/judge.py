from __future__ import annotations

import asyncio
import logging
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)

DEFAULT_JUDGE_PROMPT = """You are an expert judge evaluating the quality of an AI-generated response.

Given:
- Input Prompt: {input_prompt}
- Expected Output: {expected}
- Actual Output: {actual}

Evaluate the actual output against the expected output. Consider:
1. Correctness: Does it match the expected output semantically?
2. Completeness: Does it cover all required information?
3. Format: Is it in the right format?

Respond with ONLY a JSON object:
{{"reason": "your detailed reasoning here", "score": 0.0}}

Score should be between 0.0 (completely wrong) and 1.0 (perfect match)."""

async def judge_results(
    llm_client,
    test_results: List[Dict],  # from tester.py
    judge_model: str,
    custom_judge_prompt: Optional[str] = None,
    concurrency: int = 5,
) -> List[Dict]:
    """Judge each test result. Returns list of {index, score, reasoning, error}."""
    semaphore = asyncio.Semaphore(concurrency)
    judge_prompt_template = custom_judge_prompt or DEFAULT_JUDGE_PROMPT

    async def judge_single(result: dict) -> dict:
        async with semaphore:
            if result.get("error") or result.get("actual") is None:
                return {
                    "index": result["index"],
                    "score": 0.0,
                    "reasoning": f"Test execution failed: {result.get('error', 'No output')}",
                    "error": None,
                }
            try:
                prompt = judge_prompt_template.format(
                    input_prompt=result.get("input_prompt") or str(result["input_data"]),
                    input_data=str(result["input_data"]),
                    expected=result["expected"],
                    actual=result["actual"],
                )

                response = await llm_client.complete_json(prompt, model=judge_model, temperature=0.1)

                score = float(response.get("score", 0.0))
                score = max(0.0, min(1.0, score))  # clamp
                reasoning = response.get("reason", response.get("reasoning", "No reasoning provided"))

                return {
                    "index": result["index"],
                    "score": score,
                    "reasoning": reasoning,
                    "error": None,
                }
            except Exception as e:
                logger.error(f"Judging case {result['index']} failed: {e}")
                return {
                    "index": result["index"],
                    "score": 0.0,
                    "reasoning": f"Judge error: {e}",
                    "error": str(e),
                }

    tasks = [judge_single(r) for r in test_results]
    judgments = await asyncio.gather(*tasks)
    return sorted(judgments, key=lambda j: j["index"])
