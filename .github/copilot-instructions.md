# Repository Instructions for GitHub Copilot

## 1) High‑Level Details

**research2jira** is an AI Strategist system that converts research requests into structured Jira tasks through a guided, multi-phase workflow.

**Key Features:**

- Interactive CLI for research request processing
- 5-phase workflow: GOAL_CAPTURE → CLARIFY → PLAN_TASKS → PREVIEW → DISPATCH
- Automatic task breakdown with dependencies, effort estimates, and rationale
- Comprehensive telemetry with JSON blocks after each turn
- Sensitive data redaction (emails, credentials)
- Confidence-based early stopping in clarification phase

**Technology Stack:**

- Python 3.11+ (uses modern features like `StrEnum`, `auto()`, type hints)
- `uv` for package management
- `pydantic` for data validation
- `typer` + `rich` for CLI
- `pytest` for testing (~78% coverage, 54 tests)

## 2) Build and Validation Information

**Package Manager:** `uv` (installed automatically by Makefile if missing)

**Setup:**

```bash
make develop  # Recommended: installs deps, sets up git hooks, configures environment
# OR
uv sync && uv pip install -e .  # Manual setup
```

**Validation Pipeline:**

1. **Linting:** `make lint` or `uv run ruff check --fix`
2. **Formatting:** `make format` or `uv run ruff format`
3. **Type Checking:** `uv run mypy src/research2jira` (strict mode enabled)
4. **Testing:** `make test` or `uv run pytest tests/ --cov=research2jira`
5. **Pre-commit:** `make run-pre-commit` (runs all checks)

**Key Make Targets:**

- `make develop` - Full development setup
- `make test` / `make check` - Run tests with coverage
- `make format` - Format and lint code
- `make lint` - Lint with auto-fix
- `make clean` - Remove build artifacts

**Testing:**

- Test files: `tests/test_*.py` (models, state, phases, orchestrator, telemetry)
- Coverage target: ~78% (core logic well-tested)
- Run specific tests: `uv run pytest tests/test_phases.py -v`

## 3) Project Layout and Architecture

**Source Structure (`src/research2jira/`):**

```text
src/research2jira/
├── __init__.py          # Package exports (AIStrategist, models, enums)
├── models.py            # Data models: GoalSpec, TaskSpec, TaskSet, DispatchEnvelope
│                        # Enums: Phase, Depth, Priority, NextAction (using StrEnum)
├── state.py             # StrategistState: session state management
├── phases.py            # Phase handlers: GoalCapture, Clarify, PlanTasks, Preview, Dispatch
├── orchestrator.py      # AIStrategist: main orchestrator coordinating phases
├── telemetry.py         # Telemetry generation with redaction and fingerprinting
├── cli.py               # CLI interface (typer + rich)
└── bin/
    └── example_script.py
```

**Key Design Patterns:**

- **Phase Handlers:** Each phase has a handler class inheriting from `PhaseHandler`
- **State Management:** `StrategistState` maintains session state across turns
- **Telemetry:** Every turn emits structured JSON telemetry blocks
- **Type Safety:** Extensive use of Pydantic models and type hints

**Workflow:**

1. User provides research request → `GoalCaptureHandler`
2. System asks clarification questions → `ClarifyHandler` (stops when confidence ≥ 0.7)
3. System generates task breakdown → `PlanTasksHandler`
4. User reviews plan → `PreviewHandler` (Accept/Refine/Regenerate)
5. System emits Jira dispatch → `DispatchHandler`

**Important Implementation Notes:**

- `ClarifyHandler` records questions when asked (not just when answered) to prevent infinite loops
- Phase enum values use `auto()` (lowercase: `goal_capture`, `clarify`, etc.)
- Depth enum uses explicit values with hyphens (`executive-brief`, `tech-brief`, `deep-dive`)
- Telemetry includes SHA256 fingerprints for all artifacts

## 4) Conventional Commits and contribution workflow

**Commit message format:** `<type>(<scope>): <subject>`

**Common types:**

- `feat` - New feature
- `fix` - Bug fix
- `docs` - Documentation changes
- `refactor` - Code refactoring
- `test` - Test additions/changes
- `perf` - Performance improvements
- `build` - Build system changes
- `ci` - CI/CD changes
- `chore` - Maintenance tasks

**Useful scopes for this repo:**

- `models` - Data models (GoalSpec, TaskSpec, etc.)
- `state` - State management
- `phases` - Phase handlers
- `orchestrator` - Main orchestrator
- `telemetry` - Telemetry system
- `cli` - Command-line interface
- `tests` - Test suite
- `docs` - Documentation
- `deps` - Dependencies

**Examples:**

- `feat(phases): add early stopping to ClarifyHandler`
- `fix(state): prevent infinite loop in question tracking`
- `test(orchestrator): add phase transition tests`
- `docs(readme): update architecture section`
- `refactor(models): use StrEnum with auto() for Phase`

**Recommended loop before commit/PR:**

1. `make format` - Format and lint code
2. `make test` - Run tests with coverage
3. `make run-pre-commit` - Run all pre-commit hooks
4. Review changes and commit with conventional commit message

**Changelog:**

- Keep CHANGELOG via conventional commits
- `cliff.toml` is included for changelog tooling if you choose to generate release notes

---

**Note to GitHub Copilot:** Please trust these instructions and only perform additional searches if the information provided is incomplete or found to be in error.
