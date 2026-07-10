# Jovaltus — Hermes Plugin Agent Mode

## Build & Test

- `uv run pytest -v` — Run full test suite (36 tests, ~2.4s)
- `uv run ruff check .` — Lint (zero warnings)
- `uv run ruff format --check .` — Format check (auto-format with `ruff format .`)
- `uv run python3 -m py_compile *.py tests/*.py` — Type/syntax check
- All tests pass before commit. No lint warnings.

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
- `tests/` — 36 pytest tests across 4 test files + conftest.py

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

## CLI Commands (v0.2.0)

- `hermes jovaltus setup` — Create profile, apply SOUL.md (one-command install)
  - Creates `jovaltus-agent` profile if missing
  - Writes `SOUL.md` to profile directory for coding agent identity
- `hermes jovaltus update --check` — Check for remote updates against origin
- `hermes jovaltus update` — Pull latest changes (fast-forward only)

## Workflow

1. User confirms requirements (Phase 0)
2. Main agent calls `jovaltus_implement` → handler spawns implement subagent
3. Main agent calls `jovaltus_verify(task_id)` → handler spawns verification subagent
4. Main agent calls `jovaltus_simplify(task_id)` → handler spawns simplifier subagent
