import asyncio
import logging
from typing import Callable, Awaitable, Optional, List, Dict

from .image_loader import build_openai_image_content, build_anthropic_image_content

logger = logging.getLogger(__name__)

async def _build_image_blocks(llm_client, image_sources: list[str]) -> list[dict]:
    """Build provider-specific image content blocks."""
    from .llm_client import AnthropicLLMClient as _Anthropic
    is_anthropic = isinstance(llm_client, _Anthropic)
    builder = build_anthropic_image_content if is_anthropic else build_openai_image_content
    return [await builder(src) for src in image_sources if src]

async def run_tests(
    llm_client,  # LLMClient instance
    prompt_template: str,
    test_cases: List[Dict],  # list of {col: value} dicts from CSV
    expected_col: str,  # column name containing expected output
    model: str,
    temperature: float = 0.7,
    concurrency: int = 5,
    on_progress: Optional[Callable[[int, int], Awaitable[None]]] = None,
    image_columns: Optional[List[str]] = None,
) -> List[Dict]:
    """Run prompt_template on each test case concurrently. Returns list of {index, input_data, expected, actual, error}."""
    semaphore = asyncio.Semaphore(concurrency)
    image_cols = image_columns or []

    async def run_single(index: int, test_case: dict):
        async with semaphore:
            try:
                # Build input data (everything except expected column)
                input_data = {k: v for k, v in test_case.items() if k != expected_col}
                expected = test_case.get(expected_col, "")

                # Separate text placeholders from image columns
                text_data = {k: v for k, v in input_data.items() if k not in image_cols}

                # Format prompt with text-only placeholders
                formatted_prompt = prompt_template.format(**text_data)

                if image_cols:
                    # Build image content blocks and use vision API
                    image_sources = [input_data[col] for col in image_cols if col in input_data and input_data[col]]
                    images = await _build_image_blocks(llm_client, image_sources)
                    actual = await llm_client.complete_vision(formatted_prompt, images, model=model, temperature=temperature)
                else:
                    actual = await llm_client.complete(formatted_prompt, model=model, temperature=temperature)

                result = {
                    "index": index,
                    "input_data": input_data,
                    "expected": expected,
                    "actual": actual,
                    "error": None,
                }
            except Exception as e:
                logger.error(f"Test case {index} failed: {e}")
                result = {
                    "index": index,
                    "input_data": {k: v for k, v in test_case.items() if k != expected_col},
                    "expected": test_case.get(expected_col, ""),
                    "actual": None,
                    "error": str(e),
                }

            if on_progress:
                await on_progress(index + 1, len(test_cases))
            return result

    tasks = [run_single(i, tc) for i, tc in enumerate(test_cases)]
    results = await asyncio.gather(*tasks)
    return sorted(results, key=lambda r: r["index"])
