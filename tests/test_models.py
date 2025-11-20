"""Tests for data models."""

import pytest
from pydantic import ValidationError

from research2jira.models import (
    Depth,
    DispatchEnvelope,
    GoalSpec,
    NextAction,
    Phase,
    Priority,
    TaskSet,
    TaskSpec,
)


class TestEnums:
    """Test enum classes."""

    def test_depth_enum(self) -> None:
        """Test Depth enum values."""
        assert Depth.EXECUTIVE_BRIEF.value == "executive-brief"
        assert Depth.TECH_BRIEF.value == "tech-brief"
        assert Depth.DEEP_DIVE.value == "deep-dive"

    def test_phase_enum(self) -> None:
        """Test Phase enum values."""
        assert Phase.GOAL_CAPTURE.value == "goal_capture"
        assert Phase.CLARIFY.value == "clarify"
        assert Phase.PLAN_TASKS.value == "plan_tasks"
        assert Phase.PREVIEW.value == "preview"
        assert Phase.DISPATCH.value == "dispatch"

    def test_priority_enum(self) -> None:
        """Test Priority enum values."""
        assert Priority.HIGH.value == "High"
        assert Priority.MEDIUM.value == "Medium"
        assert Priority.LOW.value == "Low"

    def test_next_action_enum(self) -> None:
        """Test NextAction enum values."""
        assert NextAction.ASK.value == "ask"
        assert NextAction.PLAN.value == "plan"
        assert NextAction.PREVIEW.value == "preview"
        assert NextAction.AWAIT_CONFIRMATION.value == "await_confirmation"
        assert NextAction.DISPATCH.value == "dispatch"
        assert NextAction.END.value == "end"


class TestGoalSpec:
    """Test GoalSpec model."""

    def test_goal_spec_creation(self) -> None:
        """Test creating a GoalSpec."""
        goal = GoalSpec(
            topic="Test topic",
            audience="Engineers",
            deliverable="Report",
            timeframe="2 weeks",
            depth=Depth.TECH_BRIEF,
        )
        assert goal.topic == "Test topic"
        assert goal.audience == "Engineers"
        assert goal.deliverable == "Report"
        assert goal.timeframe == "2 weeks"
        assert goal.depth == Depth.TECH_BRIEF

    def test_goal_spec_defaults(self) -> None:
        """Test GoalSpec default values."""
        goal = GoalSpec(
            topic="Test",
            audience="Test",
            deliverable="Test",
            timeframe="Test",
            depth=Depth.EXECUTIVE_BRIEF,
        )
        assert goal.constraints["sources_allowed"] == ["web", "internal"]
        assert goal.constraints["forbidden"] == []
        assert goal.must_haves == []
        assert goal.must_not_haves == []
        assert goal.success_criteria == []

    def test_goal_spec_serialization(self) -> None:
        """Test GoalSpec serialization."""
        goal = GoalSpec(
            topic="Test",
            audience="Test",
            deliverable="Test",
            timeframe="Test",
            depth=Depth.DEEP_DIVE,
        )
        data = goal.model_dump(mode="json")
        assert data["topic"] == "Test"
        assert data["depth"] == "deep-dive"


class TestTaskSpec:
    """Test TaskSpec model."""

    def test_task_spec_creation(self) -> None:
        """Test creating a TaskSpec."""
        task = TaskSpec(
            id="T1",
            title="Test task",
            description="Test description",
            rationale="Test rationale",
            effort_hours=5.0,
        )
        assert task.id == "T1"
        assert task.title == "Test task"
        assert task.description == "Test description"
        assert task.rationale == "Test rationale"
        assert task.effort_hours == 5.0
        assert task.priority == Priority.MEDIUM

    def test_task_spec_defaults(self) -> None:
        """Test TaskSpec default values."""
        task = TaskSpec(
            id="T1",
            title="Test",
            description="Test",
            rationale="Test",
            effort_hours=1.0,
        )
        assert task.outputs == []
        assert task.acceptance_criteria == []
        assert task.priority == Priority.MEDIUM
        assert task.dependencies == []
        assert task.labels == ["research"]
        assert task.suggested_methods == []

    def test_task_spec_negative_effort_validation(self) -> None:
        """Test TaskSpec rejects negative effort."""
        with pytest.raises(ValidationError, match="greater than or equal to 0"):
            TaskSpec(
                id="T1",
                title="Test",
                description="Test",
                rationale="Test",
                effort_hours=-1.0,
            )


class TestTaskSet:
    """Test TaskSet model."""

    def test_task_set_creation(self) -> None:
        """Test creating a TaskSet."""
        goal = GoalSpec(
            topic="Test",
            audience="Test",
            deliverable="Test",
            timeframe="Test",
            depth=Depth.TECH_BRIEF,
        )
        task = TaskSpec(
            id="T1",
            title="Test",
            description="Test",
            rationale="Test",
            effort_hours=5.0,
        )
        task_set = TaskSet(
            goal=goal,
            tasks=[task],
            est_total_hours=5.0,
        )
        assert task_set.goal == goal
        assert len(task_set.tasks) == 1
        assert task_set.tasks[0] == task
        assert task_set.est_total_hours == 5.0
        assert task_set.subtasks == {}
        assert task_set.notes == ""
        assert task_set.risk_flags == []

    def test_task_set_negative_hours_validation(self) -> None:
        """Test TaskSet rejects negative total hours."""
        goal = GoalSpec(
            topic="Test",
            audience="Test",
            deliverable="Test",
            timeframe="Test",
            depth=Depth.TECH_BRIEF,
        )
        with pytest.raises(ValidationError, match="greater than or equal to 0"):
            TaskSet(
                goal=goal,
                tasks=[],
                est_total_hours=-1.0,
            )


class TestDispatchEnvelope:
    """Test DispatchEnvelope model."""

    def test_dispatch_envelope_creation(self) -> None:
        """Test creating a DispatchEnvelope."""
        envelope = DispatchEnvelope(
            project_key="RES",
            story={"summary": "Test story", "description": "Test description"},
        )
        assert envelope.project_key == "RES"
        assert envelope.story["summary"] == "Test story"
        assert envelope.tasks == []
        assert envelope.subtasks == {}
        assert "research-bot" in envelope.labels_global
        assert "hitl-approved" in envelope.labels_global

    def test_dispatch_envelope_with_tasks(self) -> None:
        """Test DispatchEnvelope with tasks."""
        task = TaskSpec(
            id="T1",
            title="Test",
            description="Test",
            rationale="Test",
            effort_hours=1.0,
        )
        envelope = DispatchEnvelope(
            project_key="RES",
            story={"summary": "Test", "description": "Test"},
            tasks=[task],
        )
        assert len(envelope.tasks) == 1
        assert envelope.tasks[0] == task
