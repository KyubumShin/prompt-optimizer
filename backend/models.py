from __future__ import annotations

from sqlalchemy import Column, Integer, String, Float, Text, DateTime, JSON, ForeignKey, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from typing import List, Optional
from datetime import datetime


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


class Run(Base):
    """Model for optimization runs."""
    __tablename__ = "runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, default="pending", nullable=False)  # pending|running|completed|failed|stopped
    initial_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    best_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    best_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    config: Mapped[dict] = mapped_column(JSON, nullable=False)
    dataset_filename: Mapped[str] = mapped_column(String, nullable=False)
    dataset_columns: Mapped[dict] = mapped_column(JSON, nullable=False)
    total_iterations_completed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    iterations: Mapped[List["Iteration"]] = relationship("Iteration", back_populates="run", cascade="all, delete-orphan")
    logs: Mapped[List["Log"]] = relationship("Log", back_populates="run", cascade="all, delete-orphan")


class Iteration(Base):
    """Model for individual iterations within a run."""
    __tablename__ = "iterations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    run_id: Mapped[int] = mapped_column(Integer, ForeignKey("runs.id"), nullable=False)
    iteration_num: Mapped[int] = mapped_column(Integer, nullable=False)
    prompt_template: Mapped[str] = mapped_column(Text, nullable=False)
    avg_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    min_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    max_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    improvement_reasoning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    improver_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    run: Mapped["Run"] = relationship("Run", back_populates="iterations")
    test_results: Mapped[List["TestResult"]] = relationship("TestResult", back_populates="iteration", cascade="all, delete-orphan")


class TestResult(Base):
    """Model for individual test results within an iteration."""
    __tablename__ = "test_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    iteration_id: Mapped[int] = mapped_column(Integer, ForeignKey("iterations.id"), nullable=False)
    test_case_index: Mapped[int] = mapped_column(Integer, nullable=False)
    input_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    expected_output: Mapped[str] = mapped_column(Text, nullable=False)
    actual_output: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    judge_reasoning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    iteration: Mapped["Iteration"] = relationship("Iteration", back_populates="test_results")


class Log(Base):
    """Model for system logs."""
    __tablename__ = "logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    run_id: Mapped[int] = mapped_column(Integer, ForeignKey("runs.id"), nullable=False)
    iteration_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("iterations.id"), nullable=True)
    stage: Mapped[str] = mapped_column(String, nullable=False)  # test|judge|summarize|improve|system
    level: Mapped[str] = mapped_column(String, nullable=False)  # info|warn|error
    message: Mapped[str] = mapped_column(Text, nullable=False)
    data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    run: Mapped["Run"] = relationship("Run", back_populates="logs")
