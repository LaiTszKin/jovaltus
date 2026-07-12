# Project Structure — Jovaltus

| Directory | Responsibility | Key Files |
|-----------|---------------|-----------|
| `src/jovaltus/` | Plugin source — entry, tools, state, hooks, schemas | `__init__.py`, `tools.py`, `state.py` |
| `src/jovaltus/prompts/` | Subagent system prompts (editable without touching Python) | `implement.md`, `verify.md`, `simplify.md` |
| `src/jovaltus/skills/` | Bundled Hermes skills (4 skills) | `jovaltus-agent/`, `agentic-debugging/`, `manage-agents-md/`, `project-documentation/` |
| `tests/` | Pytest suite (68 tests) | `conftest.py`, `test_state.py`, `test_tools.py`, `test_schemas.py` |
| `tests/integration/` | CLI integration tests | `test_cli.py`, `conftest.py` |
| `tests/evals/` | Docker-based pipeline evaluation | `test_jovaltus_skills.py`, `tasks.py`, `rubrics.py` |
| `.pre-commit-config.yaml` | Pre-commit hooks: ruff check → mypy → ruff format | — |
| `pyproject.toml` | Project config: deps, build, tooling, entry points | — |
| `src/jovaltus/plugin.yaml` | Plugin metadata (name, version, tools list) | — |
| `src/jovaltus/SOUL.md` | Agent identity file applied during `setup` | — |

## Entry Point

```
hermes_agent.plugins → jovaltus = "jovaltus"  (pyproject.toml:17-18)
```

Hermes calls `jovaltus.register(ctx)` at startup.

## Dependency Graph (by import)

```
__init__.py
  ├── fabricium.HermesPlugin (self-bootstrapped)
  ├── hooks (on_post_tool_call, on_pre_llm_call)
  ├── schemas (IMPLEMENT_SCHEMA, VERIFY_SCHEMA, SIMPLIFY_SCHEMA)
  ├── tools (make_implement_handler, make_verify_handler, make_simplify_handler)
  │     ├── fabricium.git_utils (get_diff, get_diff_stat, get_head_hash, is_git_repo)
  │     └── state (create_task, get_task, set_stage, set_active_task, get_active_task)
  └── hooks
        └── state (get_active_task, get_stage, set_stage, set_active_task, STAGE_ORDER)
```

## How to Update

- New module added? → Add row to directory table
- Directory renamed or repurposed? → Update table + grep for imports referencing old path
- Import chain changes? → Update dependency graph

## Find It Fast

```bash
ls src/jovaltus/            # Top-level modules
grep -rn '^from \. import' src/jovaltus/  # Internal imports
grep -rn '^from fabricium' src/jovaltus/  # External imports
```
