# Hooks & Schemas

Two tightly-coupled support modules: hooks inject pipeline guidance into the main agent;
schemas define what the LLM sees when it considers calling a Jovaltus tool.

## Hooks

**Purpose:** Soft enforcement of pipeline sequencing — the agent always knows its
current stage and what to do next, but is never forced.

**Source:** `src/jovaltus/hooks.py` (182 lines)

### Public API

| Function | Signature | Description |
|----------|-----------|-------------|
| `on_post_tool_call(tool_name, args, result, task_id, **kwargs)` | `(...) -> None` | Detect Jovaltus tool returns; update stage |
| `on_pre_llm_call(session_id, user_message, **kwargs)` | `(...) -> dict \| None` | Inject stage banner context before LLM turns |

### Stage Labels & Hints

`src/jovaltus/hooks.py:25-58`

Each stage has a display label and a list of hints:

| Stage | Label | Key Hints |
|-------|-------|-----------|
| `idle` | Idle | "Ready to start. Call `jovaltus_implement()`." |
| `implement` | Implement | "Wait for subagent report. Then `jovaltus_verify(task_id=...)`." |
| `verify` | Verify & Fix | "Three-Layer Protocol running. Wait for composite report." |
| `simplify` | Simplify | "Wait for subagent report. Pipeline completion next." |
| `done` | Complete | "Pipeline complete! Start new task with `jovaltus_implement()`." |

### Stage Banner Format

Before each LLM turn when a task is active:

```
## Jovaltus Pipeline — 🔧 Implement

**Task:** `jt-1720000000000-1`
**Stage:** `implement`
**Progress:** ~~implement~~ ✓ → **verify** ← active → simplify → done

**Guidance:**
- Implement subagent is running — wait for its report.
- When it finishes, review the changes, then call `jovaltus_verify(task_id=...)`.
```

### Hook Lifecycle

```
User message
  → pre_llm_call: inject banner if active task exists
  → LLM generates response (sees banner as context)
  → LLM calls jovaltus_implement(task_id=...)
  → Tool executes, returns JSON
  → post_tool_call: parse JSON, extract task_id, set_stage, set_active_task
  → LLM receives tool result
  → pre_llm_call: inject updated banner with new stage
```

### Patterns & Gotchas

- **Commit mode bypasses post_tool_call:** Commit-mode results lack a `task_id` field.
  `on_post_tool_call` logs a warning and returns early — no stage transition.
- **Hardcoded stage labels in hooks, not state.** `_STAGE_LABELS` and `_STAGE_HINTS`
  are purely presentation layer; `state.STAGE_ORDER` is the authoritative sequence.
- **Banner includes emoji in labels:** The stage labels include emoji (`🔧`, `🔍`, `🧹`)
  because the banner is injected into the LLM's system context (not the docs).

---

## Schemas

**Purpose:** Tool JSON schemas that define how the LLM discovers and calls Jovaltus tools.

**Source:** `src/jovaltus/schemas.py` (162 lines)

### Public API

| Constant | Tool | Parameters |
|----------|------|------------|
| `IMPLEMENT_SCHEMA` | `jovaltus_implement` | `project_dir?`, `plan?` |
| `VERIFY_SCHEMA` | `jovaltus_verify` | `task_id?`, `before?`, `after?`, `project_dir?` |
| `SIMPLIFY_SCHEMA` | `jovaltus_simplify` | `task_id?`, `before?`, `after?`, `project_dir?` |

### Schema Structure

Each schema is a `dict` with:
- `name` — tool identifier
- `description` — when to call + invocation modes + constraints (rendered to LLM as tool description)
- `parameters` — JSON Schema `{"type": "object", "properties": {...}}`

### Verify/Simplify Dual-Mode Description

```
Two invocation modes:
1. task_id mode: Pass a task_id from jovaltus_implement.
   Enforces pipeline stage ordering (requires stage 'implement'/'verify').
2. commit mode: Pass 'before' (and optionally 'after') commit hashes.
   Bypasses stage validation for greater flexibility.
   'after' defaults to HEAD when only 'before' is given.

task_id and before are mutually exclusive — provide one or the other.
```

## Dependencies (hooks.py)

### Imports
| Module | Used For |
|--------|----------|
| `state` | `get_active_task`, `get_stage`, `set_stage`, `set_active_task`, `STAGE_ORDER` |
| `json`, `logging` | Parse tool results, log transitions |

### Imported By (both)
| Module | Used For |
|--------|----------|
| `__init__` | Registered via `ctx.register_hook(...)` and `ctx.register_tool(...)` |

## Patterns & Gotchas

- **Schemas are pure data:** No functions, no imports from other Jovaltus modules.
  They're loaded by `__init__.py` at import time.
- **Description doubles as LLM prompt:** The `description` field in each schema is the
  primary mechanism for teaching the LLM when and how to call each tool. Changes to
  descriptions directly affect agent behavior.
- **Hooks use `Any` kwargs:** `on_post_tool_call` and `on_pre_llm_call` accept `**kwargs`
  to remain compatible with future Hermes hook signature changes.

## How to Update

- New tool added? → Add schema constant to `schemas.py`
- Tool parameters changed? → Update `properties` dict + description
- Hook signature changed by Hermes? → Update callback signatures
- Stage label/hint changed? → Update `_STAGE_LABELS` / `_STAGE_HINTS`

## Find It Fast

```bash
grep -n 'def on_' src/jovaltus/hooks.py              # Hook callbacks
grep -n '_SCHEMA =' src/jovaltus/schemas.py           # Schema definitions
grep -n 'description' src/jovaltus/schemas.py         # LLM-facing descriptions
```
