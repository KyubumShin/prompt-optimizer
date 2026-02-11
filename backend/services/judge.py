import asyncio
import logging
from typing import Optional, List, Dict

from .image_loader import build_openai_image_content, build_anthropic_image_content

logger = logging.getLogger(__name__)

DEFAULT_JUDGE_PROMPT = """You are an expert judge evaluating the quality of an AI-generated response.

Given:
- Input: {input_data}
- Expected Output: {expected}
- Actual Output: {actual}

Evaluate the actual output against the expected output. Consider:
1. Correctness: Does it match the expected output semantically?
2. Completeness: Does it cover all required information?
3. Format: Is it in the right format?

Respond with ONLY a JSON object:
{{"reason": "your detailed reasoning here", "score": 0.0}}

Score should be between 0.0 (completely wrong) and 1.0 (perfect match)."""

DEFAULT_VLM_JUDGE_PROMPT = """You are an expert judge evaluating a Vision Language Model's response to a visual question/task.

Given:
- Image(s): [attached above]
- Input: {input_data}
- Expected Output: {expected}
- Actual Output: {actual}

Evaluate the actual output against the expected output, considering both the image content and the expected output. Consider:
1. Correctness: Does it match the expected output semantically given the image?
2. Completeness: Does it cover all required information visible in the image?
3. Visual Accuracy: Does the response correctly interpret the visual content?
4. Format: Is it in the right format?

Respond with ONLY a JSON object:
{{"reason": "your detailed reasoning here", "score": 0.0}}

Score should be between 0.0 (completely wrong) and 1.0 (perfect match)."""

async def _build_image_blocks(llm_client, image_sources: list[str]) -> list[dict]:
    """Build provider-specific image content blocks for judge."""
    from .llm_client import AnthropicLLMClient as _Anthropic
    is_anthropic = isinstance(llm_client, _Anthropic)
    builder = build_anthropic_image_content if is_anthropic else build_openai_image_content
    return [await builder(src) for src in image_sources if src]

async def judge_results(
    llm_client,
    test_results: List[Dict],  # from tester.py
    judge_model: str,
    custom_judge_prompt: Optional[str] = None,
    concurrency: int = 5,
    image_columns: Optional[List[str]] = None,
) -> List[Dict]:
    """Judge each test result. Returns list of {index, score, reasoning, error}."""
    semaphore = asyncio.Semaphore(concurrency)
    image_cols = image_columns or []
    is_vlm = bool(image_cols)

    # Select appropriate judge prompt
    if custom_judge_prompt:
        judge_prompt_template = custom_judge_prompt
    elif is_vlm:
        judge_prompt_template = DEFAULT_VLM_JUDGE_PROMPT
    else:
        judge_prompt_template = DEFAULT_JUDGE_PROMPT

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
                    input_data=str(result["input_data"]),
                    expected=result["expected"],
                    actual=result["actual"],
                )

                if is_vlm:
                    # Include original images so the judge can see what the VLM saw
                    image_sources = [result["input_data"][col] for col in image_cols if col in result["input_data"] and result["input_data"][col]]
                    images = await _build_image_blocks(llm_client, image_sources)
                    response = await llm_client.complete_json_vision(prompt, images, model=judge_model, temperature=0.1)
                else:
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
