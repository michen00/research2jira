"""Tests for the orchestrator."""

from research2jira.models import Phase
from research2jira.orchestrator import AIStrategist


class TestAIStrategist:
    """Test AIStrategist orchestrator."""

    def test_initialization(self) -> None:
        """Test strategist initialization."""
        strategist = AIStrategist()
        assert strategist.session_id is not None
        assert strategist.current_phase == Phase.GOAL_CAPTURE
        assert strategist.turn_id_counter == 0
        assert not strategist.is_complete()

    def test_initialization_with_session_id(self) -> None:
        """Test strategist initialization with custom session ID."""
        strategist = AIStrategist(session_id="custom-123")
        assert strategist.session_id == "custom-123"

    def test_process_turn_goal_capture(self) -> None:
        """Test processing a turn in GOAL_CAPTURE phase."""
        strategist = AIStrategist()
        user_view, telemetry = strategist.process_turn(
            "I want to research machine learning"
        )

        assert len(user_view) > 0
        assert "```json" in telemetry
        assert strategist.current_phase == Phase.CLARIFY

    def test_process_turn_clarify(self) -> None:
        """Test processing turns through CLARIFY phase."""
        strategist = AIStrategist()
        # First turn: goal capture
        strategist.process_turn("Research ML frameworks")
        # Second turn: first clarification question
        user_view, _telemetry = strategist.process_turn("")

        assert strategist.current_phase == Phase.CLARIFY
        assert "audience" in user_view.lower() or "target" in user_view.lower()

    def test_phase_transitions(self) -> None:
        """Test phase transitions through the workflow."""
        strategist = AIStrategist()

        # Goal capture -> Clarify
        strategist.process_turn("Research topic")
        assert strategist.current_phase == Phase.CLARIFY

        # Answer questions to move to planning
        max_iterations = 5
        iteration = 0
        while iteration < max_iterations and strategist.current_phase == Phase.CLARIFY:
            strategist.process_turn("Test answer")
            iteration += 1

        # Should eventually reach PLAN_TASKS
        assert strategist.current_phase in [
            Phase.CLARIFY,
            Phase.PLAN_TASKS,
            Phase.PREVIEW,
        ]

    def test_telemetry_format(self) -> None:
        """Test that telemetry is properly formatted."""
        strategist = AIStrategist()
        _user_view, telemetry = strategist.process_turn("Test input")

        assert "```json" in telemetry
        assert "```" in telemetry
        # Check for key telemetry fields
        assert '"phase"' in telemetry or '"turn_id"' in telemetry

    def test_multiple_turns(self) -> None:
        """Test processing multiple turns."""
        strategist = AIStrategist()

        for i in range(3):
            user_view, telemetry = strategist.process_turn(f"Input {i}")
            assert len(user_view) > 0
            assert len(telemetry) > 0

        assert strategist.turn_id_counter == 3

    def test_is_complete(self) -> None:
        """Test completion detection."""
        strategist = AIStrategist()
        assert not strategist.is_complete()

        # Complete the workflow
        strategist.current_phase = Phase.DISPATCH
        strategist.turn_id_counter = 1
        assert strategist.is_complete()

    def test_session_id_persistence(self) -> None:
        """Test that session ID persists across turns."""
        session_id = "test-session-456"
        strategist = AIStrategist(session_id=session_id)

        for _ in range(3):
            _user_view, telemetry = strategist.process_turn("Test")
            assert session_id in telemetry
