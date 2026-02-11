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
- Specific Issues: {specific_issues}
- Suggestions: {suggestions}

The prompt template uses {{placeholder}} variables (e.g., {{input}}, {{text}}) that get filled with test case data. You MUST preserve all existing placeholder variables.

Available placeholder variables: {available_columns}

Generate an improved version of the prompt that addresses the identified issues. Respond with ONLY a JSON object:
{{
    "reasoning": "Explain what you changed and why",
    "improved_prompt": "The full improved prompt template with {{placeholders}} preserved"
}}"""

VLM_IMPROVEMENT_GUIDANCE = """

NOTE: This prompt is used with a Vision Language Model (VLM) that receives images alongside the text prompt.
Consider VLM-specific improvements:
- Add explicit references to visual content (e.g., "Looking at the image...", "Based on what you see...")
- Encourage step-by-step visual reasoning (e.g., "First describe what you see, then answer...")
- Include spatial description hints (e.g., "Pay attention to text, labels, and spatial relationships in the image")
- Be specific about what visual elements to focus on
- Do NOT add image placeholders - images are provided separately as visual input"""

async def improve_prompt(
    llm_client,
    current_prompt: str,
    summary: Dict,
    available_columns: List[str],
    model: str,
    target_score: float = 0.9,
    summary_language: str = "English",
    is_vlm: bool = False,
) -> Dict:
    """Generate improved prompt based on failure summary. Returns {reasoning, improved_prompt}."""
    prompt = IMPROVE_PROMPT.format(
        current_prompt=current_prompt,
        avg_score=summary["avg_score"],
        target_score=target_score,
        failure_patterns=", ".join(summary.get("failure_patterns", [])),
        specific_issues=", ".join(summary.get("specific_issues", [])),
        suggestions=", ".join(summary.get("suggestions", [])),
        available_columns=", ".join(available_columns),
    )

    if is_vlm:
        prompt += VLM_IMPROVEMENT_GUIDANCE

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
    }
