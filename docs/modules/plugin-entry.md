# Plugin Entry

**Purpose:** Hermes plugin registration entry point — wires tools, hooks, CLI commands,
and bundled skills together at startup.

**Source:** `src/jovaltus/__init__.py` (86 lines) + `src/jovaltus/plugin.yaml`

## Public API

| Entity | Signature | Description |
|--------|-----------|-------------|
| `register(ctx)` | `(ctx: Any) -> None` | Main entry point; registers 3 tools, 2 hooks, CLI, skills |
| `plugin` | `HermesPlugin(name="jovaltus", ...)` | Fabricium plugin instance (CLI + skills auto-discovered) |

## Registration Flow

```
Hermes starts
  → import jovaltus
    → _ensure_fabricium() — self-bootstrap if missing
    → from fabricium import HermesPlugin
    → from . import hooks, schemas
    → from .tools import make_*_handler
  → jovaltus.register(ctx)
    → plugin.register(ctx)       — Fabricium: CLI commands + bundled skills
    → ctx.register_tool(...) x3  — Tools: implement, verify, simplify
    → ctx.register_hook(...) x2  — Hooks: post_tool_call, pre_llm_call
```

## Self-Bootstrap (`_ensure_fabricium`)

`src/jovaltus/__init__.py:19-29`

When Hermes recreates its venv (e.g., during an update), plugin-only dependencies
like `fabricium` may be dropped. `_ensure_fabricium()` catches `ImportError`,
runs `pip install --upgrade fabricium`, and clears stale import cache.

| Scenario | Action |
|----------|--------|
| `fabricium` import succeeds | No-op |
| `fabricium` import fails | `pip install --upgrade fabricium`, clear `sys.modules` |

## Plugin Metadata (`plugin.yaml`)

`src/jovaltus/plugin.yaml:1-8`

| Field | Value |
|-------|-------|
| `name` | `jovaltus` |
| `version` | `0.5.0` |
| `provides_tools` | `jovaltus_implement`, `jovaltus_verify`, `jovaltus_simplify` |

## Registered Tools

| Tool Name | Schema | Handler Factory |
|-----------|--------|-----------------|
| `jovaltus_implement` | `schemas.IMPLEMENT_SCHEMA` | `tools.make_implement_handler(ctx)` |
| `jovaltus_verify` | `schemas.VERIFY_SCHEMA` | `tools.make_verify_handler(ctx)` |
| `jovaltus_simplify` | `schemas.SIMPLIFY_SCHEMA` | `tools.make_simplify_handler(ctx)` |

All three in toolset `"jovaltus"`.

## Registered Hooks

| Hook | Callback | Purpose |
|------|----------|---------|
| `post_tool_call` | `hooks.on_post_tool_call` | Detect Jovaltus tool returns, update pipeline stage |
| `pre_llm_call` | `hooks.on_pre_llm_call` | Inject stage guidance banner before each LLM turn |

## Dependencies

### Imports
| Module | Used For |
|--------|----------|
| `fabricium.HermesPlugin` | Plugin registration: CLI + bundled skills |
| `hooks` | `on_post_tool_call`, `on_pre_llm_call` |
| `schemas` | `IMPLEMENT_SCHEMA`, `VERIFY_SCHEMA`, `SIMPLIFY_SCHEMA` |
| `tools` | `make_implement_handler`, `make_verify_handler`, `make_simplify_handler` |

### Imported By
| Module | Used For |
|--------|----------|
| Hermes runtime | Calls `jovaltus.register(ctx)` at startup |

## Patterns & Gotchas

- **Self-bootstrap order matters:** `_ensure_fabricium()` runs BEFORE the `from fabricium import ...` line.
  The `# noqa: E402` comments are intentional — ruff would flag an import not at top-of-file.
- **Closure factory pattern:** All handlers are closures created in `register()`, capturing `ctx`.
  Prompts are loaded at factory creation time, not at invocation time.
- **Two-tier registration:** `plugin.register(ctx)` (Fabricium) handles generic Hermes plugin
  concerns (CLI, skills); the rest handles Jovaltus-specific tools and hooks. This separation
  avoids duplicating CLI registration code.
- **Bundled skills auto-discovered:** Fabricium scans `skills/` directory tree for `SKILL.md`
  files with YAML frontmatter. No manual registration needed.
- **No class-based plugin:** Everything uses functions + closures. No `Plugin` class, no
  inheritance from a base plugin class.

## How to Update

- New tool added? → Add `ctx.register_tool(...)` call + new import from `schemas`
- New hook added? → Add `ctx.register_hook(...)` call
- CLI command added? → Handled by Fabricium — add to `plugin.yaml` or Fabricium config
- Bundled skill added/removed? → Add/remove directory under `src/jovaltus/skills/`

## Find It Fast

```bash
grep -n 'register_tool\|register_hook' src/jovaltus/__init__.py  # All registrations
grep -n '_ensure_fabricium' src/jovaltus/__init__.py              # Bootstrap guard
ls src/jovaltus/skills/                                           # Bundled skills list
```
