"""Tests for state management."""

from research2jira.models import Depth, GoalSpec
from research2jira.state import StrategistState


class TestStrategistState:
    """Test StrategistState class."""

    def test_state_initialization(self) -> None:
        """Test state initialization."""
        state = StrategistState("test-session-123")
        assert state.session_id == "test-session-123"
        assert state.goal_spec is None
        assert state.goal_spec_partial == {}
        assert state.prior_answers == []
        assert state.questions_asked == []
        assert state.slots_filled == []
        assert state.assumptions == []
        assert state.task_set is None
        assert state.turn_count == 0

    def test_update_goal_spec(self) -> None:
        """Test updating goal spec."""
        state = StrategistState("test")
        goal = GoalSpec(
            topic="Test topic",
            audience="Engineers",
            deliverable="Report",
            timeframe="2 weeks",
            depth=Depth.TECH_BRIEF,
        )
        state.update_goal_spec(goal)
        assert state.goal_spec == goal
        assert state.goal_spec_partial == goal.model_dump(mode="json")

    def test_add_answer(self) -> None:
        """Test adding question-answer pairs."""
        state = StrategistState("test")
        state.add_answer("What is the topic?", "Machine learning")
        assert len(state.prior_answers) == 1
        assert state.prior_answers[0]["question"] == "What is the topic?"
        assert state.prior_answers[0]["answer"] == "Machine learning"
        assert "What is the topic?" in state.questions_asked

    def test_mark_slot_filled(self) -> None:
        """Test marking slots as filled."""
        state = StrategistState("test")
        state.mark_slot_filled("topic")
        assert "topic" in state.slots_filled
        state.mark_slot_filled("topic")  # Should not duplicate
        assert state.slots_filled.count("topic") == 1

    def test_add_assumption(self) -> None:
        """Test adding assumptions."""
        state = StrategistState("test")
        state.add_assumption("Web sources are available")
        assert "Web sources are available" in state.assumptions
        state.add_assumption("Web sources are available")  # Should not duplicate
        assert state.assumptions.count("Web sources are available") == 1

    def test_compute_confidence_no_slots(self) -> None:
        """Test confidence computation with no slots filled."""
        state = StrategistState("test")
        confidence = state.compute_confidence()
        assert confidence == 0.0

    def test_compute_confidence_partial(self) -> None:
        """Test confidence computation with partial slots."""
        state = StrategistState("test")
        state.mark_slot_filled("topic")
        state.mark_slot_filled("audience")
        confidence = state.compute_confidence()
        assert confidence == 0.4  # 2 out of 5 slots

    def test_compute_confidence_all_slots(self) -> None:
        """Test confidence computation with all slots filled."""
        state = StrategistState("test")
        for slot in ["topic", "audience", "deliverable", "timeframe", "depth"]:
            state.mark_slot_filled(slot)
        confidence = state.compute_confidence()
        assert confidence == 1.0

    def test_to_dict(self) -> None:
        """Test state to dictionary conversion."""
        state = StrategistState("test")
        state.mark_slot_filled("topic")
        state.add_answer("Question?", "Answer")
        state.add_assumption("Test assumption")
        state.goal_spec_partial = {"topic": "Test"}

        state_dict = state.to_dict()
        assert "goal_spec_partial" in state_dict
        assert "prior_answers" in state_dict
        assert "questions_asked" in state_dict
        assert "slots_filled" in state_dict
        assert "assumptions" in state_dict
        assert state_dict["slots_filled"] == ["topic"]
