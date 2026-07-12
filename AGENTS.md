# Jovaltus — Hermes Plugin Agent Mode

## Build & Test

- `uv run pytest -v` — Run full test suite (80 tests)
- `uv run ruff check .` — Lint
- `uv run ruff format --check .` — Format check
- `uv run mypy` — Type check (strict mode, config in `pyproject.toml`)
- Pre-commit runs lint → mypy → format on commit. Run manually: `pre-commit run --all-files`
- All checks must pass before commit. Zero warnings on lint, type, and format.

## Tech Stack

- **Language**: Python 3.10+
- **Package manager**: uv
- **Framework**: fabricium ≥0.1.1 (Hermes plugin SDK — `HermesPlugin`, `git_utils`)
- **Testing**: pytest ≥8 with fabricium test harness
- **Lint/Format**: ruff ≥0.8 + mypy ≥1.16 (`--strict` via `pyproject.toml`)
- **Build**: hatchling (src layout)

## Project Structure

- `src/jovaltus/` — Plugin package (src layout; root is NOT the package)
- `src/jovaltus/__init__.py` + `plugin.yaml` — Plugin entry point
- `src/jovaltus/tools.py` — Tool handler factories (implement, verify, simplify); dual-mode: task_id + commit-based
- `src/jovaltus/schemas.py` — Tool JSON schemas for LLM consumption
- `src/jovaltus/state.py` — Thread-safe in-memory task state
- `src/jovaltus/hooks.py` — Plugin lifecycle hooks
- `src/jovaltus/prompts/*.md` — Subagent system prompts (editable without touching Python)
- `src/jovaltus/skills/` — Bundled agent skills (e.g. `jovaltus-agent`)
- `tests/` — 80 pytest tests across 7 test files + conftest.py

## Key Constraints

- All handler functions must accept `(args: dict, **kwargs)` and return JSON string
- All git commands use list args (no `shell=True`) — enforced by `fabricium.git_utils`
- State uses `threading.Lock` for thread safety
- Handler factories capture `ctx` in `register()` — closures, not class instances
- Prompt files loaded at factory creation time, not at handler invocation
- Plugin skills are namespaced (`jovaltus:jovaltus-agent`), loaded via `skill_view()`

## Documentation

- `docs/features/` — User-visible behaviour in BDD format (Given/When/Then)
- `docs/architecture/` — Module boundaries and design principles
- `docs/principles/` — Code conventions with source evidence
- Every doc claim traces to source file + line range. `[INFERRED]` marks unverifiable claims.

## Workflow

The Jovaltus pipeline has two modes:

**Stateful (task_id):** Phase 0 confirmation → `jovaltus_implement` → `jovaltus_verify(task_id)` → `jovaltus_simplify(task_id)`

**Stateless (commit mode):** `jovaltus_verify(before=<hash>)` / `jovaltus_simplify(before=<hash>)` — operates on any commit range, no pipeline state. `task_id` and `before` are mutually exclusive.

For detailed CLI commands (`hermes jovaltus setup`, `status`, `update`), see `README.md`.

## Boundaries

**Always:**
- Run tests before committing
- Add tests for new behaviour
- Match existing code style (ruff + mypy enforce this)

**Ask first:**
- Adding new dependencies
- Changing the plugin API surface (schemas, tool signatures)
- Modifying the bundled skill (`src/jovaltus/skills/jovaltus-agent/SKILL.md`)

**Never:**
- Commit `.env` files or secrets
- Use `shell=True` in subprocess calls
- Edit `generated/` or `__pycache__/` directories
