"""Main orchestrator for the AI Strategist system."""

import uuid

from research2jira.models import DispatchEnvelope, NextAction, Phase
from research2jira.phases import (
    ClarifyHandler,
    DispatchHandler,
    GoalCaptureHandler,
    PhaseHandler,
    PlanTasksHandler,
    PreviewHandler,
)
from research2jira.state import StrategistState
from research2jira.telemetry import Telemetry

__all__ = ("AIStrategist",)


class AIStrategist:
    """Main orchestrator for the AI Strategist system."""

    def __init__(self, session_id: str | None = None) -> None:
        """Initialize the strategist."""
        self.session_id = session_id or str(uuid.uuid4())
        self.state = StrategistState(self.session_id)
        self.current_phase = Phase.GOAL_CAPTURE
        self.turn_id_counter = 0

    def process_turn(self, user_input: str) -> tuple[str, str]:
        """Process a user turn.

        Returns:
            Tuple of (user_view, telemetry_json_block)
        """
        self.turn_id_counter += 1
        turn_id = f"turn-{self.turn_id_counter:03d}"

        # Get appropriate handler
        handler = self._get_handler()

        # Process the turn
        user_view, decisions, next_action = handler.process(user_input)

        # Determine next phase
        next_phase = self._determine_next_phase(next_action)

        # Get artifacts for telemetry
        goal_spec = self.state.goal_spec
        task_set = self.state.task_set
        dispatch_envelope: DispatchEnvelope | None = getattr(
            self.state, "dispatch_envelope", None
        )

        # Create telemetry
        telemetry = Telemetry.create(
            session_id=self.session_id,
            turn_id=turn_id,
            phase=self.current_phase,
            raw_user_utterance=user_input,
            state=self.state.to_dict(),
            decisions=decisions,
            user_view=user_view,
            goal_spec=goal_spec,
            task_set=task_set,
            dispatch_envelope=dispatch_envelope,
            next_action=next_action,
        )

        # Update phase for next turn
        self.current_phase = next_phase

        return user_view, telemetry.to_json_block()

    def _get_handler(self) -> PhaseHandler:
        """Get the appropriate phase handler."""
        handlers: dict[Phase, type[PhaseHandler]] = {
            Phase.GOAL_CAPTURE: GoalCaptureHandler,
            Phase.CLARIFY: ClarifyHandler,
            Phase.PLAN_TASKS: PlanTasksHandler,
            Phase.PREVIEW: PreviewHandler,
            Phase.DISPATCH: DispatchHandler,
        }
        handler_class = handlers.get(self.current_phase)
        if not handler_class:
            msg = f"Unknown phase: {self.current_phase}"
            raise ValueError(msg)
        return handler_class(self.state)

    def _determine_next_phase(self, next_action: NextAction) -> Phase:
        """Determine the next phase based on next_action."""
        phase_map = {
            NextAction.ASK: Phase.CLARIFY,
            NextAction.PLAN: Phase.PLAN_TASKS,
            NextAction.PREVIEW: Phase.PREVIEW,
            NextAction.AWAIT_CONFIRMATION: Phase.PREVIEW,
            NextAction.DISPATCH: Phase.DISPATCH,
            NextAction.END: Phase.DISPATCH,  # Stay in DISPATCH after completion
        }

        # Special handling for initial goal capture
        if self.current_phase == Phase.GOAL_CAPTURE and next_action == NextAction.ASK:
            return Phase.CLARIFY

        return phase_map.get(next_action, self.current_phase)

    def is_complete(self) -> bool:
        """Check if the strategist has completed its workflow."""
        return self.current_phase == Phase.DISPATCH and self.turn_id_counter > 0
