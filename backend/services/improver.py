from __future__ import annotations

import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

IMPROVE_PROMPT = """You are an expert prompt engineer. Your task is to improve a prompt template based on evaluation feedback.

Current Prompt Template:
---
{current_prompt}
---

Performance Summary:
- Average Score: {avg_score:.2f} (target: {target_score:.2f})
- Failure Patterns: {failure_patterns}
- Success Patterns: {success_patterns}
- Specific Issues: {specific_issues}
- Suggestions: {suggestions}

{judge_reasoning_section}

The prompt template uses {{placeholder}} variables (e.g., {{input}}, {{text}}) that get filled with test case data. You MUST preserve all existing placeholder variables.

Available placeholder variables: {available_columns}

Generate an improved version of the prompt that addresses the identified issues while preserving what already works well. Respond with ONLY a JSON object:
{{
    "reasoning": "Explain what you changed and why",
    "improved_prompt": "The full improved prompt template with {{placeholders}} preserved"
}}"""

FAILURE_SCORE_THRESHOLD = 0.7


def _build_judge_reasoning_section(
    judge_results_list: List[Dict],
    test_results_data: List[Dict],
) -> str:
    """Build a detailed judge reasoning section for the improver prompt."""
    if not judge_results_list or not test_results_data:
        return ""

    lines = ["Judge Reasoning Details:"]

    # Failures first (most important for improvement)
    failures = []
    low_successes = []
    for test, judge in zip(test_results_data, judge_results_list):
        score = judge["score"]
        if score < FAILURE_SCORE_THRESHOLD:
            failures.append((test, judge))
        elif score < 0.9:
            low_successes.append((test, judge))

    if failures:
        lines.append("\n--- Failed Cases (score < 0.7) ---")
        for test, judge in failures:
            lines.append(
                f"  Case {test['index']}: score={judge['score']:.2f}\n"
                f"    Input: {test['input_data']}\n"
                f"    Expected: {test['expected']}\n"
                f"    Actual: {test.get('actual', 'N/A')}\n"
                f"    Judge Reasoning: {judge['reasoning']}"
            )

    if low_successes:
        lines.append("\n--- Low-Scoring Successes (0.7 <= score < 0.9) ---")
        for test, judge in low_successes:
            lines.append(
                f"  Case {test['index']}: score={judge['score']:.2f}\n"
                f"    Input: {test['input_data']}\n"
                f"    Expected: {test['expected']}\n"
                f"    Actual: {test.get('actual', 'N/A')}\n"
                f"    Judge Reasoning: {judge['reasoning']}"
            )

    return "\n".join(lines)


async def improve_prompt(
    llm_client,
    current_prompt: str,
    summary: Dict,
    available_columns: List[str],
    model: str,
    target_score: float = 0.9,
    summary_language: str = "English",
    judge_results_list: List[Dict] | None = None,
    test_results_data: List[Dict] | None = None,
) -> Dict:
    """Generate improved prompt based on failure summary. Returns {reasoning, improved_prompt, improver_prompt}."""
    judge_reasoning_section = _build_judge_reasoning_section(
        judge_results_list or [], test_results_data or []
    )

    prompt = IMPROVE_PROMPT.format(
        current_prompt=current_prompt,
        avg_score=summary["avg_score"],
        target_score=target_score,
        failure_patterns=", ".join(summary.get("failure_patterns", [])),
        success_patterns=", ".join(summary.get("success_patterns", [])),
        specific_issues=", ".join(summary.get("specific_issues", [])),
        suggestions=", ".join(summary.get("suggestions", [])),
        available_columns=", ".join(available_columns),
        judge_reasoning_section=judge_reasoning_section,
    )

    # Include user feedback if available
    if summary.get("user_feedback"):
        prompt += f"\n\nUser Feedback:\n{summary['user_feedback']}"

    if summary_language and summary_language != "English":
        prompt += f"\n\nIMPORTANT: Write your reasoning in {summary_language}."

    response = await llm_client.complete_json(prompt, model=model, temperature=0.7)

    improved = response.get("improved_prompt", current_prompt)
    reasoning = response.get("reasoning", "No reasoning provided")

    if improved == current_prompt or not improved.strip():
        logger.warning("Improver returned same or empty prompt, keeping current")
        improved = current_prompt

    return {
        "reasoning": reasoning,
        "improved_prompt": improved,
        "improver_prompt": prompt,
    }
