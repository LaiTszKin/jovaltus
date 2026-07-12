# Pipeline State

**Purpose:** Thread-safe in-memory task state with a stage machine that governs
pipeline progression: idle → implement → verify → simplify → done.

**Source:** `src/jovaltus/state.py` (168 lines)

## Public API

### Stage Machine

| Function | Signature | Description |
|----------|-----------|-------------|
| `set_stage(task_id, stage)` | `(str, str) -> bool` | Set stage with transition validation; idempotent |
| `get_stage(task_id)` | `(str) -> str \| None` | Get current stage; `None` if task not found |
| `get_next_stage(task_id)` | `(str) -> str \| None` | Next expected stage; `None` if at terminal |
| `get_current_stage()` | `() -> str \| None` | Stage of active task; `None` if none active |

### Active Task Tracking

| Function | Signature | Description |
|----------|-----------|-------------|
| `set_active_task(task_id)` | `(str \| None) -> None` | Set or clear the active task reference |
| `get_active_task()` | `() -> dict \| None` | Get active task record; `None` if none |

### CRUD

| Function | Signature | Description |
|----------|-----------|-------------|
| `create_task(project_dir, start_hash)` | `(str, str) -> str` | Create task record, return `task_id` |
| `get_task(task_id)` | `(str) -> dict \| None` | Lookup by ID |
| `task_count()` | `() -> int` | Number of active tasks |
| `clear_tasks()` | `() -> int` | Remove all tasks + clear active reference |

## Stage Machine Rules

### Valid Transitions

```
idle      → implement
implement → verify, idle
verify    → simplify, idle
simplify  → done, idle
done      → idle
```

| From | To | Allowed? |
|------|----|----------|
| idle | implement | Yes |
| implement | verify | Yes |
| implement | idle | Yes (reset) |
| verify | simplify | Yes |
| verify | idle | Yes (reset) |
| simplify | done | Yes |
| simplify | idle | Yes (reset) |
| done | idle | Yes |
| idle | verify | No — must go through implement |
| implement | simplify | No — must go through verify |

### Idempotency

`set_stage(task_id, "implement")` when already in `"implement"` → returns `True` (no-op success).

### Stage Order Constant

```python
STAGE_ORDER = ["idle", "implement", "verify", "simplify", "done"]
```

Used by `hooks.py` to build progress bars.

## Task Record Shape

```python
{
    "task_id": "jt-1720000000000-1",
    "project_dir": "/absolute/path/to/repo",
    "start_hash": "a1b2c3d...",
    "created_at": 1720000000.0,
    "stage": "implement",
}
```

| Field | Type | Set By |
|-------|------|--------|
| `task_id` | `str` | `create_task` (generated) |
| `project_dir` | `str` | `create_task` (caller) |
| `start_hash` | `str` | `create_task` (caller) |
| `created_at` | `float` | `create_task` (`time.time()`) |
| `stage` | `str` | `create_task` (init `"idle"`), `set_stage` (transitions) |

Task ID format: `jt-<unix_ms>-<increment>` — collision-resistant within a single process.

## Thread Safety

All state mutations use `threading.Lock`:

| Shared State | Mutex |
|-------------|-------|
| `_tasks` dict | `_lock` |
| `_counter` | `_lock` |
| `_current_task_id` | `_lock` |

## Dependencies

### Imports
| Module | Used For |
|--------|----------|
| `threading` | `Lock` for thread safety |
| `time` | Task timestamp |

### Imported By
| Module | Used For |
|--------|----------|
| `tools` | Create tasks, validate stages, spawn subagents |
| `hooks` | Track active task, inject stage guidance |

## Patterns & Gotchas

- **In-memory only:** State does not survive plugin reload or process restart.
  No persistence layer, no file-based state.
- **Single active task:** `_current_task_id` is a single slot, not a stack.
  Starting a new task overwrites the previous active reference.
- **`clear_tasks` resets everything:** Both `_tasks` and `_current_task_id` are cleared.
  Used by test fixtures (`autouse` in `conftest.py`).
- **No reference counting:** The `stage` field is a simple string, not an enum.
  Invalid stages cause silent `False` from `set_stage()` rather than exceptions.

## How to Update

- New stage added? → Add to `STAGE_ORDER`, `_VALID_TRANSITIONS`, `_NEXT_STAGE`
- Task record fields changed? → Update `create_task` + Task Record Shape table
- Lock usage changes? → Verify all shared-state mutations are guarded

## Find It Fast

```bash
grep -n 'def ' src/jovaltus/state.py          # All functions
grep -n 'STAGE_ORDER' src/jovaltus/state.py    # Stage definitions
grep -n 'with _lock' src/jovaltus/state.py     # Thread safety guards
```
