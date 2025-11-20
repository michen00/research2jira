"""Tests for telemetry system."""

import json

from research2jira.models import Depth, DispatchEnvelope, GoalSpec, Phase
from research2jira.telemetry import Telemetry


class TestTelemetry:
    """Test Telemetry class."""

    def test_telemetry_creation(self) -> None:
        """Test creating telemetry."""
        telemetry = Telemetry.create(
            session_id="test-123",
            turn_id="turn-001",
            phase=Phase.GOAL_CAPTURE,
            raw_user_utterance="Test input",
            state={"test": "state"},
            decisions={"confidence": 0.5},
            user_view="Test output",
        )

        assert telemetry.session_id == "test-123"
        assert telemetry.turn_id == "turn-001"
        assert telemetry.phase == Phase.GOAL_CAPTURE
        assert telemetry.inputs["raw_user_utterance"] == "Test input"
        assert telemetry.decisions["confidence"] == 0.5

    def test_telemetry_with_goal_spec(self) -> None:
        """Test telemetry with GoalSpec artifact."""
        goal = GoalSpec(
            topic="Test",
            audience="Test",
            deliverable="Test",
            timeframe="Test",
            depth=Depth.TECH_BRIEF,
        )
        telemetry = Telemetry.create(
            session_id="test",
            turn_id="turn-001",
            phase=Phase.CLARIFY,
            raw_user_utterance="Test",
            state={},
            decisions={},
            user_view="Test output",
            goal_spec=goal,
        )

        assert "goal_spec" in telemetry.artifacts
        assert telemetry.artifacts["goal_spec"]["topic"] == "Test"
        assert "goal_spec" in telemetry.io_fingerprints["artifact_hashes"]

    def test_telemetry_json_block(self) -> None:
        """Test telemetry JSON block formatting."""
        telemetry = Telemetry.create(
            session_id="test",
            turn_id="turn-001",
            phase=Phase.GOAL_CAPTURE,
            raw_user_utterance="Test",
            state={},
            decisions={},
            user_view="Test output",
        )

        json_block = telemetry.to_json_block()
        assert json_block.startswith("```json")
        assert json_block.endswith(("```\n", "```"))
        # Extract JSON and parse it
        json_str = json_block.replace("```json", "").replace("```", "").strip()
        data = json.loads(json_str)
        assert data["session_id"] == "test"
        assert data["turn_id"] == "turn-001"

    def test_telemetry_redaction(self) -> None:
        """Test that sensitive information is redacted."""
        telemetry = Telemetry.create(
            session_id="test",
            turn_id="turn-001",
            phase=Phase.GOAL_CAPTURE,
            raw_user_utterance="Contact me at test@example.com",
            state={},
            decisions={},
            user_view="Test output",
        )

        # Check if email was redacted
        utterance = telemetry.inputs["raw_user_utterance"]
        if "[EMAIL_REDACTED]" in utterance:
            assert telemetry.redactions["applied"] is True
            assert "email" in telemetry.redactions["fields"]

    def test_telemetry_fingerprints(self) -> None:
        """Test that fingerprints are generated."""
        telemetry = Telemetry.create(
            session_id="test",
            turn_id="turn-001",
            phase=Phase.GOAL_CAPTURE,
            raw_user_utterance="Test",
            state={},
            decisions={},
            user_view="Test output",
        )

        assert "input_hash" in telemetry.io_fingerprints
        assert telemetry.io_fingerprints["input_hash"].startswith("sha256-")
        assert len(telemetry.io_fingerprints["input_hash"]) > 10
        assert "output_hash" in telemetry.io_fingerprints
        assert telemetry.io_fingerprints["output_hash"].startswith("sha256-")
        assert len(telemetry.io_fingerprints["output_hash"]) > 10

    def test_telemetry_defaults(self) -> None:
        """Test telemetry default values."""
        telemetry = Telemetry.create(
            session_id="test",
            turn_id="turn-001",
            phase=Phase.GOAL_CAPTURE,
            raw_user_utterance="Test",
            state={},
            decisions={},
            user_view="Test output",
        )

        assert telemetry.limits["clarifier_max"] == 5
        assert telemetry.limits["confidence_threshold"] == 0.7
        assert telemetry.redactions["applied"] is False
        assert telemetry.performance["latency_ms"] == 0

    def test_telemetry_timestamp(self) -> None:
        """Test that timestamp is properly formatted."""
        telemetry = Telemetry.create(
            session_id="test",
            turn_id="turn-001",
            phase=Phase.GOAL_CAPTURE,
            raw_user_utterance="Test",
            state={},
            decisions={},
            user_view="Test output",
        )

        assert "T" in telemetry.timestamp_iso  # ISO format
        assert len(telemetry.timestamp_iso) > 10

    def test_telemetry_with_dispatch_envelope(self) -> None:
        """Test telemetry with DispatchEnvelope."""
        envelope = DispatchEnvelope(
            project_key="RES",
            story={"summary": "Test", "description": "Test"},
        )
        telemetry = Telemetry.create(
            session_id="test",
            turn_id="turn-001",
            phase=Phase.DISPATCH,
            raw_user_utterance="Test",
            state={},
            decisions={},
            user_view="Test output",
            dispatch_envelope=envelope,
        )

        assert "dispatch_envelope" in telemetry.artifacts
        assert telemetry.artifacts["dispatch_envelope"]["project_key"] == "RES"
        assert "dispatch_envelope" in telemetry.io_fingerprints["artifact_hashes"]
