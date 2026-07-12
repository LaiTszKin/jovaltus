# Tool Handlers

**Purpose:** Factory functions that create tool handler closures. Each handler validates
pipeline stage, computes git diffs, reads subagent prompts, and spawns subagents via
`ctx.dispatch_tool("delegate_task", ...)`.

**Source:** `src/jovaltus/tools.py` (493 lines)

## Public API

| Function | Signature | Description |
|----------|-----------|-------------|
| `make_implement_handler(ctx)` | `(ctx) -> Callable[..., str]` | Factory for `jovaltus_implement` handler |
| `make_verify_handler(ctx)` | `(ctx) -> Callable[..., str]` | Factory for `jovaltus_verify` handler (dual-mode) |
| `make_simplify_handler(ctx)` | `(ctx) -> Callable[..., str]` | Factory for `jovaltus_simplify` handler (dual-mode) |

## Internal Helpers

| Function | Signature | Description |
|----------|-----------|-------------|
| `_read_prompt(name)` | `(str) -> str` | Read system prompt from `prompts/<name>.md` |
| `_resolve_dir(project_dir)` | `(str \| None) -> str` | Resolve project directory, default to cwd |
| `_resolve_commit_range(before, after)` | `(str, str \| None) -> tuple[str, str]` | Default `after` to `"HEAD"` |
| `_spawn_review_subagent(ctx, ...)` | `(...) -> str` | Shared logic for verify/simplify in task_id mode |
| `_spawn_commit_review_subagent(ctx, ...)` | `(...) -> str` | Shared logic for verify/simplify in commit mode |
| `_validate_task_id_before_exclusive(task_id, before)` | `(str, str) -> str \| None` | Mutual exclusivity check |

## Two Invocation Modes

### Task ID Mode (Stateful)

```
jovaltus_implement(plan, project_dir?)
  1. Validate: no active task (or stage idle/done)
  2. Record: create_task(dir, start_hash), set_stage("implement")
  3. Spawn: implement subagent with plan + project context
  4. Return: {task_id, start_hash, subagent: "spawned"}

jovaltus_verify(task_id, project_dir?)
  1. Validate: stage == "implement"
  2. Compute: git diff start_hash..HEAD
  3. Spawn: verify subagent with diff context + toolsets=[terminal, file, computer_use]
  4. Return: {task_id, start_hash, diff, files_changed}

jovaltus_simplify(task_id, project_dir?)
  1. Validate: stage == "verify"
  2. Compute: git diff start_hash..HEAD
  3. Spawn: simplify subagent with diff context
  4. Return: {task_id, start_hash, diff, files_changed}
```

### Commit Mode (Stateless)

```
jovaltus_verify(before, after?, project_dir?)
  → Compute before..after diff directly
  → Spawn verify subagent (no stage validation, no state)
  → Return: {before, after, diff, pipeline_mode: false}

jovaltus_simplify(before, after?, project_dir?)
  → Same pattern, different prompt + toolsets
```

**Constraints:**
- `task_id` and `before` are mutually exclusive (`_validate_task_id_before_exclusive`)
- `after` defaults to `"HEAD"` when only `before` is given
- Commit mode subagents receive `toolsets=[terminal, file, computer_use]` (verify) or `[terminal, file]` (simplify)

## Error Responses

| Condition | Response |
|-----------|----------|
| Active task in non-idle/done stage | `{"error": "Cannot start IMPLEMENT: task '...' is in stage '...'"}` |
| Not a git repo | `{"error": "Not a git repository: ..."}` |
| Task not found | `{"error": "Task '...' not found. Did you call jovaltus_implement first?"}` |
| Wrong stage for verify/simplify | `{"error": "Cannot start VERIFY: task '...' is in stage '...'"}` |
| Both task_id and before provided | `{"error": "Provide task_id or before, not both."}` |
| Neither provided for verify/simplify | `{"error": "Provide task_id (pipeline mode) or before (commit-based mode)."}` |
| Stage transition rejected | `{"error": "Stage transition ... → verify rejected."}` |
| Unexpected exception | `{"error": str(e)}` logged via `logger.exception` |

## Dependencies

### Imports
| Module | Used For |
|--------|----------|
| `fabricium.git_utils` | `get_diff`, `get_diff_stat`, `get_head_hash`, `is_git_repo` |
| `state` | `create_task`, `get_task`, `set_stage`, `set_active_task`, `get_active_task` |

### Imported By
| Module | Used For |
|--------|----------|
| `__init__` | `register()` calls all three `make_*_handler(ctx)` factories |

## Patterns & Gotchas

- **Closure over ctx:** Handler functions are inner functions that close over `ctx` and `prompt`.
  Created once in `register()`; reused for all tool calls.
- **Prompts loaded once:** `_read_prompt("implement")` runs in `make_implement_handler()`,
  not in the inner `handler()`. Edits to prompt files require a plugin reload to take effect.
- **Shared spawn logic:** `_spawn_review_subagent` and `_spawn_commit_review_subagent` are
  near-identical apart from state lookup and error handling. [INFERRED] Kept separate because
  the error paths differ significantly and merging would add conditional complexity.
- **Commit mode bypasses hooks:** `post_tool_call` won't receive a `task_id` from commit-mode
  results (field is absent), so no stage transition is triggered. This is intentional — commit
  mode is stateless.
- **Implement spawns with NULL diff:** Unlike verify/simplify, `jovaltus_implement` doesn't
  compute a diff. It passes the `plan` and project context directly.

## How to Update

- New handler mode added? → Add validation logic + new `_spawn_*` helper
- Prompt file path changed? → Update `_PROMPTS_DIR` constant
- toolsets changed? → Update `toolsets` parameter in `_spawn_*_subagent` calls
- Error message changed? → Update Error Responses table

## Find It Fast

```bash
grep -n 'def make_' src/jovaltus/tools.py          # Handler factories
grep -n 'dispatch_tool' src/jovaltus/tools.py       # Subagent spawn points
grep -n 'return json.dumps({"error"' src/jovaltus/tools.py  # All error returns
```
