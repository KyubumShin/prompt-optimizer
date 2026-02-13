from __future__ import annotations

import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

FAILURE_SCORE_THRESHOLD = 0.7

SUMMARIZE_PROMPT = """You are analyzing the results of a prompt evaluation. Below are the judge evaluations for each test case.

Current prompt being evaluated:
{prompt_template}

Test Results Summary:
- Average Score: {avg_score:.2f}
- Min Score: {min_score:.2f}
- Max Score: {max_score:.2f}
- Total Cases: {total_cases}
- Failed Cases (score < 0.7): {failed_count}

Detailed Failures (score < 0.7):
{failure_details}

Analyze the failure patterns and provide a JSON response:
{{
    "summary": "Brief overview of performance",
    "failure_patterns": ["pattern1", "pattern2"],
    "specific_issues": ["issue1", "issue2"],
    "suggestions": ["suggestion1", "suggestion2"]
}}"""

async def summarize_results(
    llm_client,
    prompt_template: str,
    test_results: List[Dict],  # combined test + judge results
    judge_results_list: List[Dict],
    model: str,
    summary_language: str = "English",
) -> Dict:
    """Aggregate judge reasoning into failure patterns. Returns summary dict."""
    scores = [j["score"] for j in judge_results_list]
    avg_score = sum(scores) / len(scores) if scores else 0.0
    min_score = min(scores) if scores else 0.0
    max_score = max(scores) if scores else 0.0

    # Collect failures
    failures = []
    for test, judge in zip(test_results, judge_results_list):
        if judge["score"] < FAILURE_SCORE_THRESHOLD:
            failures.append(
                f"  Case {test['index']}: score={judge['score']:.2f}\n"
                f"    Input: {test['input_data']}\n"
                f"    Expected: {test['expected']}\n"
                f"    Actual: {test.get('actual', 'N/A')}\n"
                f"    Reasoning: {judge['reasoning']}"
            )

    failure_details = "\n".join(failures) if failures else "No significant failures."

    prompt = SUMMARIZE_PROMPT.format(
        prompt_template=prompt_template,
        avg_score=avg_score,
        min_score=min_score,
        max_score=max_score,
        total_cases=len(test_results),
        failed_count=len(failures),
        failure_details=failure_details,
    )

    if summary_language and summary_language != "English":
        prompt += f"\n\nIMPORTANT: Write your response in {summary_language}."

    response = await llm_client.complete_json(prompt, model=model, temperature=0.3)

    return {
        "avg_score": avg_score,
        "min_score": min_score,
        "max_score": max_score,
        "summary": response.get("summary", ""),
        "failure_patterns": response.get("failure_patterns", []),
        "specific_issues": response.get("specific_issues", []),
        "suggestions": response.get("suggestions", []),
    }
