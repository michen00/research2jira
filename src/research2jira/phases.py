"""Phase handlers for the AI Strategist."""

from typing import Any

from research2jira.models import (
    Depth,
    DispatchEnvelope,
    GoalSpec,
    NextAction,
    Priority,
    TaskSet,
    TaskSpec,
)
from research2jira.state import StrategistState

__all__ = (
    "ClarifyHandler",
    "DispatchHandler",
    "GoalCaptureHandler",
    "PhaseHandler",
    "PlanTasksHandler",
    "PreviewHandler",
)


class PhaseHandler:
    """Base class for phase handlers."""

    def __init__(self, state: StrategistState) -> None:
        """Initialize handler with state."""
        self.state = state

    def process(self, user_input: str) -> tuple[str, dict[str, Any], NextAction]:
        """Process user input and return (user_view, decisions, next_action)."""
        raise NotImplementedError


class GoalCaptureHandler(PhaseHandler):
    """Handle GOAL_CAPTURE phase."""

    def process(self, user_input: str) -> tuple[str, dict[str, Any], NextAction]:
        """Extract initial GoalSpec from user input."""
        # Simple extraction - in production, use LLM
        # For now, create a partial spec and move to CLARIFY
        decisions = {
            "confidence": 0.3,
            "stop_clarifying": False,
            "skipped_questions": [],
            "reasoning_factors": ["initial extraction"],
            "warnings": [],
        }

        # Extract basic info (simplified - would use LLM in production)
        topic = user_input[:200]  # Simplified
        self.state.goal_spec_partial = {"topic": topic}
        self.state.mark_slot_filled("topic")

        user_view = (
            "I've captured your research request. Let me ask a few questions "
            "to better understand your needs.\n\n"
        )

        return user_view, decisions, NextAction.ASK


class ClarifyHandler(PhaseHandler):
    """Handle CLARIFY phase."""

    def __init__(self, state: StrategistState) -> None:
        """Initialize with state."""
        super().__init__(state)
        self.clarification_questions = [
            ("audience", "Who is the target audience for this research?"),
            (
                "deliverable",
                "What specific deliverable do you need? "
                "(e.g., report, presentation, analysis)",
            ),
            ("timeframe", "What is your timeframe for completion?"),
            (
                "depth",
                "What depth of research do you need? "
                "(executive-brief, tech-brief, deep-dive)",
            ),
        ]

    def _normalize_depth(self, depth_input: str) -> Depth:
        """Normalize and validate depth input, returning a valid Depth enum."""
        if not depth_input:
            return Depth.TECH_BRIEF

        # Normalize: lowercase and replace spaces with hyphens
        normalized = depth_input.lower().strip().replace(" ", "-")

        # Try to match valid enum values
        try:
            return Depth(normalized)
        except ValueError:
            # Try fuzzy matching for common variations
            # Order matters: check more specific/longer keywords first
            depth_map = [
                ("executive", Depth.EXECUTIVE_BRIEF),
                ("technical", Depth.TECH_BRIEF),
                ("detailed", Depth.DEEP_DIVE),
                ("exec", Depth.EXECUTIVE_BRIEF),
                ("tech", Depth.TECH_BRIEF),
                ("deep", Depth.DEEP_DIVE),
                ("dive", Depth.DEEP_DIVE),
                ("brief", Depth.EXECUTIVE_BRIEF),  # Check last as it's ambiguous
            ]
            # Check if input contains any of the keywords (in order)
            for keyword, depth_enum in depth_map:
                if keyword in normalized:
                    return depth_enum

            # Default to tech-brief if no match found
            return Depth.TECH_BRIEF

    def process(self, user_input: str) -> tuple[str, dict[str, Any], NextAction]:
        """Process clarification answer or ask next question."""
        questions_asked_count = len(self.state.questions_asked)

        # If this is the first question, just ask it (don't process user_input)
        if questions_asked_count == 0:
            slot, question = self.clarification_questions[0]
            # Record that we're asking this question
            self.state.add_question(question)
            user_view = f"{question}\n"
            decisions = {
                "confidence": self.state.compute_confidence(),
                "stop_clarifying": False,
                "skipped_questions": [],
                "reasoning_factors": ["first clarification question"],
                "warnings": [],
            }
            return user_view, decisions, NextAction.ASK

        # Process the answer for the last question
        if questions_asked_count > 0 and questions_asked_count <= len(
            self.clarification_questions
        ):
            slot, question = self.clarification_questions[questions_asked_count - 1]
            self.state.add_answer(question, user_input)
            # Normalize depth input if this is the depth question
            if slot == "depth":
                normalized_depth = self._normalize_depth(user_input)
                self.state.goal_spec_partial[slot] = normalized_depth.value
            else:
                self.state.goal_spec_partial[slot] = user_input
            self.state.mark_slot_filled(slot)

        # Compute confidence
        confidence = self.state.compute_confidence()
        questions_remaining = len(self.clarification_questions) - len(
            self.state.questions_asked
        )

        # Check if we should stop
        stop_clarifying = confidence >= 0.7 or questions_remaining == 0

        decisions = {
            "confidence": confidence,
            "stop_clarifying": stop_clarifying,
            "skipped_questions": [],
            "reasoning_factors": ["slot completeness", "confidence threshold"],
            "warnings": [],
        }

        if stop_clarifying:
            # Build complete GoalSpec
            partial = self.state.goal_spec_partial
            # Validate and normalize depth value
            depth_value = self._normalize_depth(partial.get("depth", "tech-brief"))
            goal_spec = GoalSpec(
                topic=partial.get("topic", "Unknown"),
                audience=partial.get("audience", "General"),
                deliverable=partial.get("deliverable", "Research report"),
                timeframe=partial.get("timeframe", "Not specified"),
                depth=depth_value,
            )
            self.state.update_goal_spec(goal_spec)
            user_view = (
                "Thank you! I have enough information to create a research plan.\n\n"
            )
            return user_view, decisions, NextAction.PLAN
        # Ask next question
        slot, question = self.clarification_questions[len(self.state.questions_asked)]
        # Record that we're asking this question
        self.state.add_question(question)
        user_view = f"{question}\n"
        return user_view, decisions, NextAction.ASK


class PlanTasksHandler(PhaseHandler):
    """Handle PLAN_TASKS phase."""

    def process(self, user_input: str) -> tuple[str, dict[str, Any], NextAction]:
        """Generate TaskSet from GoalSpec."""
        _ = user_input  # Unused but required by interface
        if not self.state.goal_spec:
            msg = "GoalSpec not available for planning"
            raise ValueError(msg)

        goal = self.state.goal_spec

        # Generate tasks (simplified - would use LLM in production)
        tasks = self._generate_tasks(goal)
        subtasks: dict[str, list[TaskSpec]] = {}

        # Calculate total hours
        est_total_hours = sum(task.effort_hours for task in tasks)

        # Check for warnings
        warnings = []
        if est_total_hours > 40:
            warnings.append("effort looks high vs typical timeframe")

        task_set = TaskSet(
            goal=goal,
            tasks=tasks,
            subtasks=subtasks,
            est_total_hours=est_total_hours,
            risk_flags=warnings,
        )
        self.state.task_set = task_set

        decisions = {
            "confidence": 0.8,
            "stop_clarifying": True,
            "skipped_questions": [],
            "reasoning_factors": ["task decomposition", "effort estimation"],
            "warnings": warnings,
        }

        # Format user view
        user_view = self._format_task_list(task_set)

        return user_view, decisions, NextAction.PREVIEW

    def _generate_tasks(self, goal: GoalSpec) -> list[TaskSpec]:
        """Generate tasks based on goal (simplified implementation)."""
        tasks = []

        # Task 1: Literature review
        tasks.append(
            TaskSpec(
                id="T1",
                title=f"Literature review: {goal.topic}",
                description=f"Conduct comprehensive literature review on {goal.topic}",
                outputs=["Annotated bibliography", "Key findings summary"],
                acceptance_criteria=[
                    "Minimum 10 sources reviewed",
                    "Key themes identified",
                ],
                priority=Priority.HIGH,
                effort_hours=8.0,
                dependencies=[],
                suggested_methods=["web search", "academic databases"],
                rationale="Foundation for understanding current state of knowledge",
            )
        )

        # Task 2: Market analysis
        tasks.append(
            TaskSpec(
                id="T2",
                title=f"Market/industry analysis: {goal.topic}",
                description=(
                    f"Analyze market trends and industry landscape for {goal.topic}"
                ),
                outputs=["Market analysis report", "Trend analysis"],
                acceptance_criteria=[
                    "Current market size identified",
                    "Key players identified",
                ],
                priority=Priority.HIGH,
                effort_hours=6.0,
                dependencies=["T1"],
                suggested_methods=["industry reports", "web search"],
                rationale="Context for understanding market position",
            )
        )

        # Task 3: Technical deep dive (if needed)
        if goal.depth in [Depth.TECH_BRIEF, Depth.DEEP_DIVE]:
            tasks.append(
                TaskSpec(
                    id="T3",
                    title=f"Technical analysis: {goal.topic}",
                    description=f"Deep technical analysis of {goal.topic}",
                    outputs=["Technical analysis document", "Architecture diagrams"],
                    acceptance_criteria=[
                        "Technical requirements documented",
                        "Implementation approaches analyzed",
                    ],
                    priority=Priority.MEDIUM,
                    effort_hours=10.0,
                    dependencies=["T1"],
                    suggested_methods=["technical documentation", "web search"],
                    rationale="Required for technical understanding",
                )
            )

        # Task 4: Synthesis and recommendations
        deps = ["T1", "T2"]
        if goal.depth in [Depth.TECH_BRIEF, Depth.DEEP_DIVE]:
            deps.append("T3")

        tasks.append(
            TaskSpec(
                id="T4",
                title=f"Synthesize findings and recommendations: {goal.topic}",
                description=(
                    f"Combine all research findings into actionable recommendations "
                    f"for {goal.audience}"
                ),
                outputs=[goal.deliverable, "Executive summary"],
                acceptance_criteria=[
                    "All key findings synthesized",
                    "Clear recommendations provided",
                ],
                priority=Priority.HIGH,
                effort_hours=6.0,
                dependencies=deps,
                suggested_methods=["analysis", "synthesis"],
                rationale="Final deliverable creation",
            )
        )

        return tasks

    def _format_task_list(self, task_set: TaskSet) -> str:
        """Format task list for user view."""
        lines = [
            "## Research Plan",
            "",
            f"**Goal**: {task_set.goal.topic}",
            f"**Audience**: {task_set.goal.audience}",
            f"**Deliverable**: {task_set.goal.deliverable}",
            f"**Estimated Total Hours**: {task_set.est_total_hours:.1f}",
            "",
            "### Tasks:",
            "",
        ]

        for task in task_set.tasks:
            lines.append(f"**{task.id}: {task.title}**")
            lines.append(f"  • Why: {task.rationale}")
            lines.append(f"  • Outputs: {', '.join(task.outputs)}")
            lines.append(f"  • Effort: {task.effort_hours} hours")
            if task.dependencies:
                lines.append(f"  • Depends on: {', '.join(task.dependencies)}")
            lines.append("")

        if task_set.risk_flags:
            lines.append("⚠️  **Warnings:**")
            lines.extend(f"  • {flag}" for flag in task_set.risk_flags)
            lines.append("")

        return "\n".join(lines)


class PreviewHandler(PhaseHandler):
    """Handle PREVIEW phase."""

    def process(self, user_input: str) -> tuple[str, dict[str, Any], NextAction]:
        """Handle user acceptance/refinement."""
        user_input_lower = user_input.lower().strip()

        decisions = {
            "confidence": 0.9,
            "stop_clarifying": True,
            "skipped_questions": [],
            "reasoning_factors": ["user confirmation"],
            "warnings": [],
        }

        if user_input_lower in ["accept", "yes", "y", "approve"]:
            user_view = "Plan accepted! Generating Jira dispatch payload...\n\n"
            return user_view, decisions, NextAction.DISPATCH
        if user_input_lower in ["refine", "edit", "modify"]:
            user_view = "Please specify what you'd like to refine.\n"
            return user_view, decisions, NextAction.ASK
        if user_input_lower in ["regenerate", "redo"]:
            user_view = "Regenerating plan...\n\n"
            return user_view, decisions, NextAction.PLAN
        user_view = (
            "Please respond with: **Accept** (to proceed), "
            "**Refine** (to modify), or **Regenerate** (to create a new plan).\n"
        )
        return user_view, decisions, NextAction.AWAIT_CONFIRMATION


class DispatchHandler(PhaseHandler):
    """Handle DISPATCH phase."""

    def process(self, user_input: str) -> tuple[str, dict[str, Any], NextAction]:
        """Generate DispatchEnvelope."""
        _ = user_input  # Unused but required by interface
        if not self.state.task_set:
            msg = "TaskSet not available for dispatch"
            raise ValueError(msg)

        task_set = self.state.task_set

        # Create story description
        story_description = self._create_story_description(task_set)

        dispatch_envelope = DispatchEnvelope(
            project_key="RES",
            story={
                "summary": (
                    f"Research: {task_set.goal.topic} for {task_set.goal.audience}"
                ),
                "description": story_description,
            },
            tasks=task_set.tasks,
            subtasks=task_set.subtasks,
        )

        decisions = {
            "confidence": 1.0,
            "stop_clarifying": True,
            "skipped_questions": [],
            "reasoning_factors": ["dispatch complete"],
            "warnings": [],
        }

        subtask_count = sum(len(subs) for subs in dispatch_envelope.subtasks.values())
        user_view = (
            f"## Jira Dispatch Ready\n\n"
            f"**Story**: {dispatch_envelope.story['summary']}\n"
            f"**Tasks**: {len(dispatch_envelope.tasks)}\n"
            f"**Subtasks**: {subtask_count}\n\n"
            f"The dispatch envelope has been generated and is available "
            f"in the telemetry output.\n"
        )

        # Store for telemetry
        self.state.dispatch_envelope = dispatch_envelope  # type: ignore[attr-defined]

        return user_view, decisions, NextAction.END

    def _create_story_description(self, task_set: TaskSet) -> str:
        """Create story description from TaskSet."""
        goal = task_set.goal
        lines = [
            "=== Research Goal ===",
            f"Topic: {goal.topic}",
            f"Audience: {goal.audience}",
            f"Deliverable: {goal.deliverable}",
            f"Timeframe: {goal.timeframe}",
            f"Depth: {goal.depth}",
            "",
            "=== Scope ===",
            "This research project includes the following tasks:",
        ]

        lines.extend(f"- {task.id}: {task.title}" for task in task_set.tasks)

        if goal.success_criteria:
            lines.append("")
            lines.append("=== Success Criteria ===")
            lines.extend(f"- {criterion}" for criterion in goal.success_criteria)

        if self.state.assumptions:
            lines.append("")
            lines.append("=== Assumptions ===")
            lines.extend(f"- {assumption}" for assumption in self.state.assumptions)

        return "\n".join(lines)
