# Jovaltus — Hermes Plugin Agent Mode

## Build & Test

- `uv run pytest -v` — Run full test suite (60 tests, ~2.7s)
- `uv run ruff check .` — Lint (zero warnings)
- `uv run ruff format --check .` — Format check (auto-format with `ruff format .`)
- `uv run mypy --strict --no-site-packages *.py` — Type check (zero errors)
- All tests pass before commit. No lint, format, or type warnings.

## Pre-commit Hooks (v0.4.0)

Three hooks run on every `git commit` in this order:

1. **ruff check — lint** (must pass, blocks commit on failure)
2. **mypy --strict — type check** (must pass, blocks commit on failure)
3. **ruff format — auto-format** (reformats staged files after checks pass)

Install: `pre-commit install` (already done)
Run manually: `pre-commit run --all-files`

## Project Structure

- `plugin.yaml` + `__init__.py` — Hermes plugin entry (root dir IS the package)
- `tools.py` — Three tool handler factories (implement, verify, simplify)
- `schemas.py` — Tool JSON schemas (what the LLM sees)
- `state.py` — Thread-safe in-memory task state
- `git_utils.py` — Git subprocess wrappers (list args, no shell=True)
  - New in v0.2.0: remote update utilities (fetch, pull, ahead/behind check)
- `SOUL.md` — Bundled agent identity file; applied to profile via `setup`
- `prompts/*.md` — Subagent system prompts (editable without touching Python)
- `skills/jovaltus-agent/SKILL.md` — Agent Mode workflow definition
- `tests/` — 44 pytest tests across 5 test files + conftest.py

## Key Constraints

- All handler functions must accept `(args: dict, **kwargs)` and return JSON string
- All git commands use list args (no `shell=True`)
- State uses `threading.Lock` for thread safety
- Handler factories capture `ctx` in `register()` — closures, not class instances
- Prompt files loaded at factory creation time, not at handler invocation
- Plugin skills are namespaced (`jovaltus:jovaltus-agent`), loaded via `skill_view()`

## Documentation

- `docs/features/` — User-visible behaviour in BDD format (Given/When/Then)
- `docs/architecture/` — Module boundaries and design principles
- `docs/principles/` — Code conventions with source evidence
- Every doc claim traces to source file + line range. `[INFERRED]` marks unverifiable claims.

## CLI Commands (v0.3.0)

- `hermes jovaltus setup` — Create profile, install bundled skills, apply SOUL.md
  - Interactive prompts with TTY detection (falls back to safe defaults)
  - Creates `jovaltus-agent` profile if missing
  - Installs bundled skills to global skills directory
  - Optionally writes `SOUL.md` to profile directory
  - Persists installation state to `~/.hermes/jovaltus_state.json`
- `hermes jovaltus status` — Show installation state per profile
  - Displays profile name, installation mode, and last updated timestamp
- `hermes jovaltus update --check` — Check for remote updates against origin
- `hermes jovaltus update` — Pull latest changes
  - Detects and removes stale bundled skills (interactive)
  - Refreshes all bundled skills
  - Re-applies SOUL.md where previously installed
  - Refreshes timestamps

## Workflow

1. User confirms requirements (Phase 0)
2. Main agent calls `jovaltus_implement` → handler spawns implement subagent
3. Main agent calls `jovaltus_verify(task_id)` → handler spawns verification subagent
4. Main agent calls `jovaltus_simplify(task_id)` → handler spawns simplifier subagent
