"""State management for AI Strategist sessions."""

from typing import Any

from research2jira.models import GoalSpec, TaskSet

__all__ = ("StrategistState",)


class StrategistState:
    """Maintains state across turns."""

    def __init__(self, session_id: str) -> None:
        """Initialize state."""
        self.session_id = session_id
        self.goal_spec: GoalSpec | None = None
        self.goal_spec_partial: dict[str, Any] = {}
        self.prior_answers: list[dict[str, str]] = []
        self.questions_asked: list[str] = []
        self.slots_filled: list[str] = []
        self.assumptions: list[str] = []
        self.task_set: TaskSet | None = None
        self.turn_count = 0

    def update_goal_spec(self, goal_spec: GoalSpec) -> None:
        """Update the goal specification."""
        self.goal_spec = goal_spec
        self.goal_spec_partial = goal_spec.model_dump(mode="json")

    def add_question(self, question: str) -> None:
        """Record that a question was asked."""
        if question not in self.questions_asked:
            self.questions_asked.append(question)

    def add_answer(self, question: str, answer: str) -> None:
        """Add a question-answer pair."""
        self.prior_answers.append({"question": question, "answer": answer})
        # Ensure question is recorded (in case add_question wasn't called)
        if question not in self.questions_asked:
            self.questions_asked.append(question)

    def mark_slot_filled(self, slot: str) -> None:
        """Mark a slot as filled."""
        if slot not in self.slots_filled:
            self.slots_filled.append(slot)

    def add_assumption(self, assumption: str) -> None:
        """Add an assumption."""
        if assumption not in self.assumptions:
            self.assumptions.append(assumption)

    def to_dict(self) -> dict[str, Any]:
        """Convert state to dictionary for telemetry."""
        return {
            "goal_spec_partial": self.goal_spec_partial,
            "prior_answers": self.prior_answers,
            "questions_asked": self.questions_asked,
            "slots_filled": self.slots_filled,
            "assumptions": self.assumptions,
        }

    def compute_confidence(self) -> float:
        """Compute confidence score based on filled slots."""
        required_slots = ["topic", "audience", "deliverable", "timeframe", "depth"]
        filled_count = sum(1 for slot in required_slots if slot in self.slots_filled)
        return filled_count / len(required_slots)
