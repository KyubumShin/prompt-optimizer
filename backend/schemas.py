from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime


class RunConfig(BaseModel):
    """Configuration for an optimization run."""
    model: Optional[str] = None
    model_provider: Optional[str] = None
    judge_model: Optional[str] = None
    judge_provider: Optional[str] = None
    improver_model: Optional[str] = None
    improver_provider: Optional[str] = None
    max_iterations: int = 10
    target_score: float = 0.9
    temperature: float = 0.7
    concurrency: int = 5
    judge_prompt: Optional[str] = None
    convergence_threshold: float = 0.02
    convergence_patience: int = 2
    human_feedback_enabled: bool = False
    summary_language: str = "English"


class RunCreate(BaseModel):
    """Schema for creating a new run."""
    name: str
    initial_prompt: str
    config: RunConfig = RunConfig()


class RunResponse(BaseModel):
    """Schema for run responses."""
    id: int
    name: str
    status: str
    initial_prompt: str
    best_prompt: Optional[str]
    best_score: Optional[float]
    config: dict
    dataset_filename: str
    dataset_columns: list
    total_iterations_completed: int
    error_message: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class IterationResponse(BaseModel):
    """Schema for iteration responses."""
    id: int
    run_id: int
    iteration_num: int
    prompt_template: str
    avg_score: Optional[float]
    min_score: Optional[float]
    max_score: Optional[float]
    summary: Optional[str]
    improvement_reasoning: Optional[str]
    improver_prompt: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TestResultResponse(BaseModel):
    """Schema for test result responses."""
    id: int
    iteration_id: int
    test_case_index: int
    input_data: dict
    expected_output: str
    actual_output: Optional[str]
    score: Optional[float]
    judge_reasoning: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LogResponse(BaseModel):
    """Schema for log responses."""
    id: int
    run_id: int
    iteration_id: Optional[int]
    stage: str
    level: str
    message: str
    data: Optional[dict]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RunDetailResponse(RunResponse):
    """Schema for detailed run responses with iterations."""
    iterations: List[IterationResponse] = []


class IterationDetailResponse(IterationResponse):
    """Schema for detailed iteration responses with test results."""
    test_results: List[TestResultResponse] = []


class FeedbackSubmit(BaseModel):
    """Schema for submitting human feedback."""
    feedback: str = ""
