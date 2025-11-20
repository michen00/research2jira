"""Telemetry system for tracking AI Strategist operations."""

import hashlib
import json
import re
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from research2jira.models import (
    DispatchEnvelope,
    GoalSpec,
    NextAction,
    Phase,
    TaskSet,
)

__all__ = ("Telemetry",)


class Telemetry(BaseModel):
    """Telemetry data for each turn."""

    session_id: str = Field(..., description="Session identifier")
    turn_id: str = Field(..., description="Turn identifier")
    phase: Phase = Field(..., description="Current phase")
    timestamp_iso: str = Field(..., description="ISO timestamp")
    inputs: dict[str, Any] = Field(..., description="Input data")
    decisions: dict[str, Any] = Field(..., description="Decision data")
    artifacts: dict[str, Any] = Field(default_factory=dict, description="Artifacts")
    io_fingerprints: dict[str, Any] = Field(..., description="I/O fingerprints")
    limits: dict[str, Any] = Field(
        default_factory=lambda: {"clarifier_max": 5, "confidence_threshold": 0.7},
        description="System limits",
    )
    redactions: dict[str, Any] = Field(
        default_factory=lambda: {"applied": False, "fields": []},
        description="Redaction information",
    )
    performance: dict[str, Any] = Field(
        default_factory=lambda: {"latency_ms": 0, "token_in": 0, "token_out": 0},
        description="Performance metrics",
    )
    next_action: NextAction = Field(..., description="Next action")

    def to_json_block(self) -> str:
        """Convert to JSON code block format."""
        json_str = json.dumps(self.model_dump(mode="json"), indent=2)
        return f"```json\n{json_str}\n```"

    @classmethod
    def create(  # noqa: PLR0913
        cls,
        session_id: str,
        turn_id: str,
        phase: Phase,
        raw_user_utterance: str,
        state: dict[str, Any],
        decisions: dict[str, Any],
        user_view: str,
        goal_spec: GoalSpec | None = None,
        task_set: TaskSet | None = None,
        dispatch_envelope: DispatchEnvelope | None = None,
        next_action: NextAction = NextAction.ASK,
    ) -> "Telemetry":
        """Create telemetry instance with automatic fingerprinting."""
        timestamp = datetime.now(UTC).isoformat()

        # Redact sensitive information
        redacted_utterance, redactions = cls._redact_sensitive(raw_user_utterance)

        # Build artifacts
        artifacts: dict[str, Any] = {}
        artifact_hashes: dict[str, str] = {}
        if goal_spec:
            artifacts["goal_spec"] = goal_spec.model_dump(mode="json")
            artifact_hashes["goal_spec"] = cls._hash_object(
                goal_spec.model_dump(mode="json")
            )
        if task_set:
            artifacts["task_set"] = task_set.model_dump(mode="json")
            artifact_hashes["task_set"] = cls._hash_object(
                task_set.model_dump(mode="json")
            )
        if dispatch_envelope:
            artifacts["dispatch_envelope"] = dispatch_envelope.model_dump(mode="json")
            artifact_hashes["dispatch_envelope"] = cls._hash_object(
                dispatch_envelope.model_dump(mode="json")
            )

        # Build inputs
        inputs = {
            "raw_user_utterance": redacted_utterance,
            "state": state,
        }

        # Build outputs for fingerprinting
        outputs = {
            "user_view": user_view,
            "decisions": decisions,
            "artifacts": artifacts,
        }

        # Compute fingerprints
        input_hash = cls._hash_object(inputs)
        output_hash = cls._hash_object(outputs)

        io_fingerprints = {
            "input_hash": input_hash,
            "output_hash": output_hash,
            "artifact_hashes": artifact_hashes,
        }

        return cls(
            session_id=session_id,
            turn_id=turn_id,
            phase=phase,
            timestamp_iso=timestamp,
            inputs=inputs,
            decisions=decisions,
            artifacts=artifacts,
            io_fingerprints=io_fingerprints,
            redactions=redactions,
            next_action=next_action,
        )

    @staticmethod
    def _hash_object(obj: Any) -> str:  # noqa: ANN401
        """Compute SHA256 hash of an object."""
        json_str = json.dumps(obj, sort_keys=True, ensure_ascii=False)
        return f"sha256-{hashlib.sha256(json_str.encode()).hexdigest()}"

    @staticmethod
    def _redact_sensitive(text: str) -> tuple[str, dict[str, Any]]:
        """Redact sensitive information from text."""
        # Simple redaction - look for common patterns
        redacted = text
        redacted_fields: list[str] = []

        # Check for potential credentials/PII patterns
        # Email addresses
        if re.search(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", text):
            redacted = re.sub(
                r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
                "[EMAIL_REDACTED]",
                redacted,
            )
            redacted_fields.append("email")

        # API keys / tokens (basic pattern)
        if re.search(
            r"(api[_-]?key|token|secret|password)\s*[:=]\s*[\w-]+",
            text,
            flags=re.IGNORECASE,
        ):
            redacted = re.sub(
                r"((api[_-]?key|token|secret|password)\s*[:=]\s*)[\w-]+",
                r"\1[REDACTED]",
                redacted,
                flags=re.IGNORECASE,
            )
            redacted_fields.append("credentials")

        applied = len(redacted_fields) > 0

        return redacted, {"applied": applied, "fields": redacted_fields}
