# Conventions — Jovaltus

Rules an agent can check against code. Only conventions that differ from or
extend Python defaults.

## Naming

| Element | Convention | Example |
|---------|-----------|---------|
| Module files | snake_case | `git_utils.py`, `test_tools.py` |
| Public functions | snake_case | `make_implement_handler`, `create_task` |
| Private functions | `_` prefix | `_read_prompt`, `_resolve_dir`, `_spawn_review_subagent` |
| Module-level constants | `UPPER_SNAKE` with `_` prefix if private | `_PLUGIN_DIR`, `_PROMPTS_DIR`, `STAGE_ORDER` |
| Task IDs | `jt-<timestamp>-<counter>` | `jt-1720000000000-1` |
| Test files | `test_<module>.py` | `test_state.py`, `test_schemas.py` |
| Test functions | `test_<behaviour>` | `test_create_task`, `test_stage_transition_valid` |

## Import Ordering

Enforced by ruff. Standard sections: stdlib → third-party → local.

```python
# stdlib
import json
import logging
from pathlib import Path

# third-party
from fabricium import HermesPlugin

# local
from . import hooks, schemas
from .tools import make_implement_handler
```

Self-bootstrap imports (`fabricium`) use `# noqa: E402` when placement after
the bootstrap guard is intentional.

## Error Handling

| Pattern | Usage |
|---------|-------|
| Return JSON error string | All handler functions return `json.dumps({"error": ...})` — never raise |
| Try/except in handlers | Top-level handler catches `Exception`, logs, returns error JSON |
| `logger.exception` | Used in `except` blocks to capture traceback |
| Validation functions | Return `str | None` — error JSON on failure, `None` on success |
| Stage validation | `set_stage()` returns `bool` — caller handles rejection |

## Git Commands

All git operations use **list args, never `shell=True`**.

```python
# Correct
subprocess.run(["git", "commit", "-m", "message"], cwd=repo)

# Never
subprocess.run("git commit -m 'message'", shell=True)
```

This is enforced by `fabricium.git_utils` which wraps all git commands.

## State Management

| Rule | Reason |
|------|--------|
| All state mutations inside `with _lock:` | `threading.Lock` for thread safety |
| Task state is in-memory only | No persistence; cleared on plugin reload |
| `clear_tasks()` also clears active task reference | Avoid dangling pointer |
| `set_stage` is idempotent (same stage → True) | Prevent spurious failure on retry |

## Factory Pattern

Handler creation uses **closures, not classes**:

```python
def make_implement_handler(ctx):
    prompt = _read_prompt("implement")      # captured at creation time

    def handler(args, **kwargs):            # closure over ctx + prompt
        ...
        ctx.dispatch_tool("delegate_task", {...})
        ...

    return handler
```

- Prompts loaded at factory creation time, not at handler invocation
- `ctx` captured once in `register()`

## Testing

| Convention | Detail |
|-----------|--------|
| `autouse` fixture clears state | `clear_task_state` fixture runs before every test |
| `git_repo` fixture creates temp repo | Isolated git repo per test via `tmp_path` |
| Fixture-based tools | `conftest.py` provides shared fixtures; no mocking by default |
| Integration tests in `tests/integration/` | Separate from unit tests |
| Eval tests in `tests/evals/` | Use `SkillEvalHarness`; require Docker + LLM API keys |

## Commit Messages

Subagent commits follow a consistent prefix:

| Phase | Commit Message |
|-------|----------------|
| Implement | `jovaltus: implement phase` |
| Verify | `jovaltus: verify & fix phase` |
| Simplify | `jovaltus: simplify phase` |

## Security

- Never commit `.env` files (no `.env` in repo — verified)
- No hardcoded API keys — eval config comes from environment variables

## Pre-commit Hook Order

```
1. ruff check (lint)  — blocks commit on failure
2. mypy --strict      — blocks commit on failure
3. ruff format        — auto-formats after checks pass
```

## How to Update

- New naming pattern adopted? → Add to Naming table
- Import style changes? → Update Import Ordering
- New error handling pattern? → Add to Error Handling
- Factory pattern changes? → Update Factory Pattern section

## Find It Fast

```bash
grep -rn 'def _' src/jovaltus/              # Private functions
grep -rn 'logger\.exception' src/jovaltus/  # Exception logging
grep -rn 'shell=True' src/jovaltus/         # Should return nothing
grep -rn 'with _lock' src/jovaltus/         # Lock usage points
```
