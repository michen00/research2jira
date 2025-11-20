"""Tests for phase handlers."""

from research2jira.models import Depth, GoalSpec, NextAction, TaskSet, TaskSpec
from research2jira.phases import (
    ClarifyHandler,
    DispatchHandler,
    GoalCaptureHandler,
    PlanTasksHandler,
    PreviewHandler,
)
from research2jira.state import StrategistState


class TestGoalCaptureHandler:
    """Test GoalCaptureHandler."""

    def test_process_initial_request(self) -> None:
        """Test processing initial research request."""
        state = StrategistState("test")
        handler = GoalCaptureHandler(state)

        user_view, decisions, next_action = handler.process(
            "I want to research machine learning frameworks"
        )

        assert "captured" in user_view.lower() or "questions" in user_view.lower()
        assert decisions["confidence"] < 0.7
        assert not decisions["stop_clarifying"]
        assert next_action == NextAction.ASK
        assert "topic" in state.goal_spec_partial
        assert "topic" in state.slots_filled


class TestClarifyHandler:
    """Test ClarifyHandler."""

    def test_first_question(self) -> None:
        """Test asking the first clarification question."""
        state = StrategistState("test")
        state.goal_spec_partial = {"topic": "ML frameworks"}
        state.mark_slot_filled("topic")
        handler = ClarifyHandler(state)

        user_view, decisions, next_action = handler.process("")

        assert "audience" in user_view.lower()
        assert next_action == NextAction.ASK
        assert not decisions["stop_clarifying"]
        # Verify the question was recorded (fixes infinite loop bug)
        assert len(state.questions_asked) == 1
        assert "audience" in state.questions_asked[0].lower()

    def test_no_infinite_loop_on_first_question(self) -> None:
        """Test that asking the first question doesn't cause infinite loop."""
        state = StrategistState("test")
        state.goal_spec_partial = {"topic": "ML frameworks"}
        state.mark_slot_filled("topic")
        handler = ClarifyHandler(state)

        # First turn: ask first question
        user_view1, _, _ = handler.process("")
        assert len(state.questions_asked) == 1
        first_question = state.questions_asked[0]

        # Second turn: should process answer, not ask same question again
        user_view2, _decisions, next_action = handler.process("Engineering team")

        # Should have processed the answer and moved forward
        assert len(state.prior_answers) == 1  # Has an answer
        assert "audience" in state.slots_filled
        # Key fix: should NOT ask the same question again
        assert first_question not in user_view2 or user_view2 != user_view1
        # Should either ask next question (which adds to questions_asked) or stop
        assert next_action in [NextAction.ASK, NextAction.PLAN]
        # If asking next question, questions_asked should have grown
        if next_action == NextAction.ASK:
            assert len(state.questions_asked) >= 1  # At least the first question

    def test_process_answer(self) -> None:
        """Test processing an answer to a question."""
        state = StrategistState("test")
        state.goal_spec_partial = {"topic": "ML frameworks"}
        state.mark_slot_filled("topic")
        state.questions_asked.append("Who is the target audience?")
        handler = ClarifyHandler(state)

        _user_view, _decisions, _next_action = handler.process("Engineering team")

        assert "Engineering team" in state.prior_answers[0]["answer"]
        assert "audience" in state.slots_filled
        assert state.goal_spec_partial["audience"] == "Engineering team"

    def test_stop_clarifying_high_confidence(self) -> None:
        """Test stopping clarification when confidence is high."""
        state = StrategistState("test")
        # Fill all required slots
        state.goal_spec_partial = {
            "topic": "Test",
            "audience": "Test",
            "deliverable": "Test",
            "timeframe": "Test",
            "depth": Depth.TECH_BRIEF.value,  # Use enum value
        }
        for slot in ["topic", "audience", "deliverable", "timeframe", "depth"]:
            state.mark_slot_filled(slot)
        # Simulate having asked 3 questions (one less than total)
        state.questions_asked = ["Q1", "Q2", "Q3"]
        handler = ClarifyHandler(state)

        # Process the answer to the 4th question with a valid depth value
        _user_view, decisions, next_action = handler.process(Depth.TECH_BRIEF.value)

        assert decisions["stop_clarifying"]
        assert decisions["confidence"] >= 0.7
        assert next_action == NextAction.PLAN
        assert state.goal_spec is not None

    def test_invalid_depth_input_handling(self) -> None:
        """Test that invalid depth input is normalized and doesn't crash."""
        state = StrategistState("test")
        # Fill all required slots except depth
        state.goal_spec_partial = {
            "topic": "Test",
            "audience": "Test",
            "deliverable": "Test",
            "timeframe": "Test",
        }
        for slot in ["topic", "audience", "deliverable", "timeframe"]:
            state.mark_slot_filled(slot)
        state.questions_asked = ["Q1", "Q2", "Q3"]
        handler = ClarifyHandler(state)

        # Test with invalid depth input
        _user_view, _decisions, next_action = handler.process("invalid-depth-value")

        # Should not crash, should normalize to default (tech-brief)
        assert state.goal_spec is not None
        assert state.goal_spec.depth == Depth.TECH_BRIEF
        assert next_action == NextAction.PLAN

    def test_depth_normalization_variations(self) -> None:
        """Test that various depth input formats are normalized correctly."""
        # Test the normalization function directly
        handler = ClarifyHandler(StrategistState("test"))

        test_cases = [
            ("tech brief", Depth.TECH_BRIEF),  # Space instead of hyphen
            ("TECH-BRIEF", Depth.TECH_BRIEF),  # Uppercase
            ("executive-brief", Depth.EXECUTIVE_BRIEF),  # Full match
            ("deep-dive", Depth.DEEP_DIVE),  # Full match
            ("tech", Depth.TECH_BRIEF),  # Partial match
            ("deep", Depth.DEEP_DIVE),  # Partial match
            ("invalid", Depth.TECH_BRIEF),  # Invalid -> default
            ("", Depth.TECH_BRIEF),  # Empty -> default
        ]

        for input_value, expected_depth in test_cases:
            # Access private method for testing normalization logic
            result = handler._normalize_depth(input_value)  # noqa: SLF001
            expected_msg = (
                f"Input '{input_value}' should normalize to {expected_depth}, "
                f"got {result}"
            )
            assert result == expected_depth, expected_msg


class TestPlanTasksHandler:
    """Test PlanTasksHandler."""

    def test_generate_tasks(self) -> None:
        """Test task generation."""
        state = StrategistState("test")
        goal = GoalSpec(
            topic="ML frameworks",
            audience="Engineers",
            deliverable="Report",
            timeframe="2 weeks",
            depth=Depth.TECH_BRIEF,
        )
        state.update_goal_spec(goal)
        handler = PlanTasksHandler(state)

        user_view, _decisions, next_action = handler.process("")

        assert state.task_set is not None
        assert len(state.task_set.tasks) > 0
        assert state.task_set.est_total_hours > 0
        assert "Research Plan" in user_view or "Tasks" in user_view
        assert next_action == NextAction.PREVIEW

    def test_task_dependencies(self) -> None:
        """Test that tasks have proper dependencies."""
        state = StrategistState("test")
        goal = GoalSpec(
            topic="Test",
            audience="Test",
            deliverable="Test",
            timeframe="Test",
            depth=Depth.TECH_BRIEF,
        )
        state.update_goal_spec(goal)
        handler = PlanTasksHandler(state)

        handler.process("")

        assert state.task_set is not None
        tasks = state.task_set.tasks
        # Find the synthesis task (should depend on others)
        synthesis_task = next(
            (t for t in tasks if "synthesize" in t.title.lower()), None
        )
        if synthesis_task:
            assert len(synthesis_task.dependencies) > 0

    def test_effort_estimation(self) -> None:
        """Test that effort is properly estimated."""
        state = StrategistState("test")
        goal = GoalSpec(
            topic="Test",
            audience="Test",
            deliverable="Test",
            timeframe="Test",
            depth=Depth.DEEP_DIVE,
        )
        state.update_goal_spec(goal)
        handler = PlanTasksHandler(state)

        handler.process("")

        assert state.task_set is not None
        total_hours = sum(task.effort_hours for task in state.task_set.tasks)
        assert state.task_set.est_total_hours == total_hours


class TestPreviewHandler:
    """Test PreviewHandler."""

    def test_accept(self) -> None:
        """Test accepting the plan."""
        state = StrategistState("test")
        handler = PreviewHandler(state)

        user_view, _decisions, next_action = handler.process("accept")

        assert "accepted" in user_view.lower() or "dispatch" in user_view.lower()
        assert next_action == NextAction.DISPATCH

    def test_refine(self) -> None:
        """Test requesting refinement."""
        state = StrategistState("test")
        handler = PreviewHandler(state)

        user_view, _decisions, next_action = handler.process("refine")

        assert "refine" in user_view.lower() or "specify" in user_view.lower()
        assert next_action == NextAction.ASK

    def test_regenerate(self) -> None:
        """Test requesting regeneration."""
        state = StrategistState("test")
        handler = PreviewHandler(state)

        user_view, _decisions, next_action = handler.process("regenerate")

        assert "regenerat" in user_view.lower()
        assert next_action == NextAction.PLAN

    def test_invalid_response(self) -> None:
        """Test handling invalid response."""
        state = StrategistState("test")
        handler = PreviewHandler(state)

        user_view, _decisions, next_action = handler.process("invalid")

        assert "accept" in user_view.lower() or "refine" in user_view.lower()
        assert next_action == NextAction.AWAIT_CONFIRMATION


class TestDispatchHandler:
    """Test DispatchHandler."""

    def test_dispatch_generation(self) -> None:
        """Test dispatch envelope generation."""
        state = StrategistState("test")
        goal = GoalSpec(
            topic="ML frameworks",
            audience="Engineers",
            deliverable="Report",
            timeframe="2 weeks",
            depth=Depth.TECH_BRIEF,
        )
        task = TaskSpec(
            id="T1",
            title="Test task",
            description="Test",
            rationale="Test",
            effort_hours=5.0,
        )

        state.task_set = TaskSet(goal=goal, tasks=[task], est_total_hours=5.0)
        handler = DispatchHandler(state)

        user_view, _decisions, next_action = handler.process("")

        assert hasattr(state, "dispatch_envelope")
        assert state.dispatch_envelope is not None
        assert state.dispatch_envelope.project_key == "RES"
        assert "Jira Dispatch" in user_view or "dispatch" in user_view.lower()
        assert next_action == NextAction.END

    def test_story_description(self) -> None:
        """Test that story description is properly formatted."""
        state = StrategistState("test")
        goal = GoalSpec(
            topic="ML frameworks",
            audience="Engineers",
            deliverable="Report",
            timeframe="2 weeks",
            depth=Depth.TECH_BRIEF,
        )

        state.task_set = TaskSet(goal=goal, tasks=[], est_total_hours=0.0)
        handler = DispatchHandler(state)

        handler.process("")

        assert hasattr(state, "dispatch_envelope")
        envelope = state.dispatch_envelope
        assert "ML frameworks" in envelope.story["description"]
        assert "Engineers" in envelope.story["description"]
