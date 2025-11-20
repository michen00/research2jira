"""Data models for the AI Strategist system."""

from enum import StrEnum, auto
from typing import Any

from pydantic import BaseModel, Field

__all__ = (
    "Depth",
    "DispatchEnvelope",
    "GoalSpec",
    "NextAction",
    "Phase",
    "Priority",
    "TaskSet",
    "TaskSpec",
)


class Depth(StrEnum):
    """Research depth levels."""

    EXECUTIVE_BRIEF = "executive-brief"
    TECH_BRIEF = "tech-brief"
    DEEP_DIVE = "deep-dive"


class Phase(StrEnum):
    """System phases."""

    GOAL_CAPTURE = auto()
    CLARIFY = auto()
    PLAN_TASKS = auto()
    PREVIEW = auto()
    DISPATCH = auto()


class Priority(StrEnum):
    """Task priority levels."""

    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class NextAction(StrEnum):
    """Next action indicators."""

    ASK = auto()
    PLAN = auto()
    PREVIEW = auto()
    AWAIT_CONFIRMATION = auto()
    DISPATCH = auto()
    END = auto()


class GoalSpec(BaseModel):
    """Research goal specification."""

    topic: str = Field(..., description="Research topic")
    audience: str = Field(..., description="Target audience")
    deliverable: str = Field(..., description="Expected deliverable")
    timeframe: str = Field(..., description="Timeframe for completion")
    depth: Depth = Field(..., description="Research depth level")
    constraints: dict[str, Any] = Field(
        default_factory=lambda: {
            "sources_allowed": ["web", "internal"],
            "forbidden": [],
        },
        description="Research constraints",
    )
    must_haves: list[str] = Field(
        default_factory=list, description="Must-have requirements"
    )
    must_not_haves: list[str] = Field(
        default_factory=list, description="Must-not-have requirements"
    )
    success_criteria: list[str] = Field(
        default_factory=list, description="Success criteria"
    )


class TaskSpec(BaseModel):
    """Individual research task specification."""

    id: str = Field(..., description="Task identifier (e.g., T1, T2)")
    title: str = Field(..., description="Task title")
    description: str = Field(..., description="Task description")
    outputs: list[str] = Field(default_factory=list, description="Expected outputs")
    acceptance_criteria: list[str] = Field(
        default_factory=list, description="Acceptance criteria"
    )
    priority: Priority = Field(default=Priority.MEDIUM, description="Task priority")
    effort_hours: float = Field(..., ge=0, description="Estimated effort in hours")
    dependencies: list[str] = Field(
        default_factory=list, description="Task dependencies (task IDs)"
    )
    labels: list[str] = Field(
        default_factory=lambda: ["research"], description="Task labels"
    )
    suggested_methods: list[str] = Field(
        default_factory=list, description="Suggested research methods"
    )
    rationale: str = Field(..., description="Rationale for this task")


class TaskSet(BaseModel):
    """Complete set of research tasks."""

    goal: GoalSpec = Field(..., description="Associated goal specification")
    tasks: list[TaskSpec] = Field(default_factory=list, description="Main tasks")
    subtasks: dict[str, list[TaskSpec]] = Field(
        default_factory=dict, description="Subtasks by parent task ID"
    )
    notes: str = Field(default="", description="Additional notes")
    est_total_hours: float = Field(..., ge=0, description="Estimated total hours")
    risk_flags: list[str] = Field(default_factory=list, description="Risk flags")


class DispatchEnvelope(BaseModel):
    """Jira dispatch payload."""

    project_key: str = Field(default="RES", description="Jira project key")
    story: dict[str, str] = Field(..., description="Story with summary and description")
    tasks: list[TaskSpec] = Field(default_factory=list, description="Tasks to create")
    subtasks: dict[str, list[TaskSpec]] = Field(
        default_factory=dict, description="Subtasks by parent task ID"
    )
    labels_global: list[str] = Field(
        default_factory=lambda: ["research-bot", "hitl-approved"],
        description="Global labels",
    )
