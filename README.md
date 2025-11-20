# research2jira

AI Strategist system that turns research requests into structured Jira tasks.

## Quick Start

Get up and running in 3 steps:

```bash
# 1. Install dependencies and set up the project
make develop

# 2. Start an interactive session
research2jira start

# 3. Enter your research request when prompted
```

**That's it!** The AI Strategist will guide you through:

- Capturing your research goal
- Asking clarifying questions
- Generating a structured task plan
- Creating a Jira dispatch payload

### Quick Example

```bash
$ research2jira start

You: I need to research machine learning frameworks for production use

AI Strategist: Who is the target audience for this research?
You: Engineering team

AI Strategist: What specific deliverable do you need?
You: Technical comparison report

AI Strategist: What is your timeframe for completion?
You: 2 weeks

AI Strategist: What depth of research do you need? (executive-brief, tech-brief, deep-dive)
You: tech-brief

AI Strategist: ## Research Plan
[Shows detailed task breakdown with dependencies, effort estimates, and rationale]

Please respond with: **Accept** (to proceed), **Refine** (to modify), or **Regenerate** (to create a new plan).

You: Accept

AI Strategist: ## Jira Dispatch Ready
✓ Story and tasks generated successfully!
```

## Overview

The AI Strategist guides users through a structured workflow to convert research requests into actionable Jira tasks:

1. **GOAL_CAPTURE** - Extract initial research goal
2. **CLARIFY** - Ask targeted questions to understand requirements (stops early when confidence ≥ 0.7)
3. **PLAN_TASKS** - Generate structured task breakdown with dependencies, effort estimates, and rationale
4. **PREVIEW** - Present plan for user review (Accept/Refine/Regenerate)
5. **DISPATCH** - Emit Jira dispatch payload with story and tasks

After every turn, the system emits machine-readable telemetry capturing inputs, outputs, decisions, and confidence metrics.

## Installation

### Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) (installed automatically by Makefile if missing)

### Setup

**Option 1: Using Make (Recommended)**

```bash
make develop
```

**Option 2: Manual Setup**

```bash
# Install dependencies
uv sync

# Install the package in editable mode
uv pip install -e .
```

## Usage

### Interactive Mode

Start an interactive session:

```bash
research2jira start
```

Or with a custom session ID:

```bash
research2jira start --session-id my-session-123
```

### Non-Interactive Mode

Process a single research request without interactive prompts:

```bash
research2jira process "Research quantum computing applications in finance"
```

With custom session ID:

```bash
research2jira process "Research topic" --session-id custom-123
```

Hide telemetry output:

```bash
research2jira process "Research topic" --no-telemetry
```

### Exiting Interactive Mode

In interactive mode, type `exit`, `quit`, or `q` to end the session, or press `Ctrl+C`.

## Architecture

The system is organized into the following modules:

- **`models.py`** - Data models and enums:
  - `GoalSpec` - Research goal specification
  - `TaskSpec` - Individual task definition
  - `TaskSet` - Complete task breakdown
  - `DispatchEnvelope` - Jira dispatch payload
  - Enums: `Phase`, `Depth`, `Priority`, `NextAction`

- **`state.py`** - Session state management:
  - `StrategistState` - Maintains state across turns
  - Tracks questions, answers, slots, and assumptions
  - Computes confidence scores

- **`phases.py`** - Phase handlers for each workflow stage:
  - `GoalCaptureHandler` - Extract initial research goal
  - `ClarifyHandler` - Ask targeted clarification questions
  - `PlanTasksHandler` - Generate structured task breakdown
  - `PreviewHandler` - Present plan for user review
  - `DispatchHandler` - Generate Jira dispatch envelope

- **`orchestrator.py`** - Main orchestrator:
  - `AIStrategist` - Coordinates phase transitions
  - Manages turn processing and telemetry generation

- **`telemetry.py`** - Telemetry system:
  - Generates JSON telemetry blocks after each turn
  - Handles sensitive data redaction
  - Computes I/O fingerprints (SHA256 hashes)

- **`cli.py`** - Command-line interface:
  - Interactive and non-interactive modes
  - Rich terminal formatting with Markdown support

## Telemetry

Every turn produces a JSON telemetry block containing:

- **Session metadata**: Session ID, turn ID, timestamp, current phase
- **Inputs**: Raw user utterance (with redaction), state snapshot
- **Decisions**: Confidence score, stop conditions, reasoning factors, warnings
- **Artifacts**: GoalSpec, TaskSet, DispatchEnvelope (when available)
- **I/O fingerprints**: SHA256 hashes for inputs, outputs, and artifacts
- **Performance**: Latency, token counts (when available)
- **Redactions**: Applied redactions for sensitive data (emails, credentials)

Telemetry blocks are emitted in a fenced JSON code block format for easy parsing and logging.

## Testing

The project includes comprehensive test coverage:

```bash
# Run all tests
make test

# Run tests with coverage report
uv run pytest tests/ --cov=research2jira --cov-report=term-missing

# Run specific test file
uv run pytest tests/test_phases.py -v
```

**Test Coverage:**

- **54 tests** covering all major components
- **~78% code coverage** (core logic well-tested)
- Tests for models, state management, phase handlers, orchestrator, and telemetry

**Test Files:**

- `test_models.py` - Data model validation and serialization
- `test_state.py` - State management and confidence computation
- `test_phases.py` - Phase handler logic and transitions
- `test_orchestrator.py` - Orchestrator workflow coordination
- `test_telemetry.py` - Telemetry generation and formatting

## Development

### Common Tasks

```bash
# Run tests
make test

# Format code
make format

# Lint code
make lint

# Run pre-commit checks
make run-pre-commit

# Clean build artifacts
make clean
```

### Using Nox (Alternative)

```bash
# Run tests
nox -s test

# Run linting
nox -s lint

# Run type checking
nox -s typecheck
```

### Available Make Targets

Run `make help` to see all available targets:

```bash
make help
```

Key targets:

- `make develop` - Set up development environment with git hooks
- `make install` - Install the project
- `make test` - Run tests with coverage
- `make format` - Format and lint code
- `make clean` - Remove build artifacts and caches

## License

See LICENSE file.
