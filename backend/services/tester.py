import asyncio
import logging
from typing import Callable, Awaitable, Optional, List, Dict

logger = logging.getLogger(__name__)

async def run_tests(
    llm_client,  # LLMClient instance
    prompt_template: str,
    test_cases: List[Dict],  # list of {col: value} dicts from CSV
    expected_col: str,  # column name containing expected output
    model: str,
    temperature: float = 0.7,
    concurrency: int = 5,
    on_progress: Optional[Callable[[int, int], Awaitable[None]]] = None,
) -> List[Dict]:
    """Run prompt_template on each test case concurrently. Returns list of {index, input_data, expected, actual, error}."""
    semaphore = asyncio.Semaphore(concurrency)
    results = []

    async def run_single(index: int, test_case: dict):
        async with semaphore:
            try:
                # Build input data (everything except expected column)
                input_data = {k: v for k, v in test_case.items() if k != expected_col}
                expected = test_case.get(expected_col, "")

                # Format prompt with test case values
                formatted_prompt = prompt_template.format(**input_data)

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
