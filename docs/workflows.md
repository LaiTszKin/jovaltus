# Workflows — Jovaltus

Step-by-step recipes for common development tasks.

## Adding a New Pipeline Tool

1. Add schema to `src/jovaltus/schemas.py` (e.g., `BENCHMARK_SCHEMA`)
2. Create handler factory in `src/jovaltus/tools.py` (e.g., `make_benchmark_handler`)
3. Write subagent prompt in `src/jovaltus/prompts/benchmark.md`
4. Register in `src/jovaltus/__init__.py` `register()`: `ctx.register_tool(...)`
5. Add to `src/jovaltus/plugin.yaml` `provides_tools` list
6. Add tests in `tests/test_benchmark.py`
7. Update `docs/modules/tool-handlers.md` Public API table

## Adding a New Pipeline Stage

1. Add to `state.STAGE_ORDER` list
2. Add transitions to `state._VALID_TRANSITIONS` and `state._NEXT_STAGE`
3. Add stage labels and hints to `hooks._STAGE_LABELS` and `hooks._STAGE_HINTS`
4. Update stage validation in all handler factories that gate on stages
5. Add tests in `tests/test_state.py`
6. Update `docs/modules/pipeline-state.md` Stage Machine Rules table
7. Update `docs/architecture.md` Pipeline Stage Machine diagram

## Adding a Bundled Skill

1. Create directory `src/jovaltus/skills/<skill-name>/`
2. Write `SKILL.md` with YAML frontmatter:
   ```yaml
   ---
   name: <skill-name>
   description: ...
   author: LaiTszKin
   version: 0.1.0
   metadata:
     jovaltus:
       tags: [...]
   ---
   ```
3. Add supporting files under `references/`, `templates/`, `scripts/` as needed
4. Fabricium auto-discovers skills — no manual registration

## Running the Full Pipeline (End-to-End)

1. Confirm requirements with user (Phase 0)
2. `jovaltus_implement(plan="<requirements>")` → implement subagent
3. Wait for subagent report → review changes
4. `jovaltus_verify(task_id="<id>")` → verify subagent (Three-Layer Protocol)
5. Wait for composite verification report
6. If ALL-PASS → `jovaltus_simplify(task_id="<id>")` → simplify subagent
7. Wait for simplification report

## Running Verify/Simplify in Commit Mode

```bash
# Verify changes since a commit
jovaltus_verify(before="<commit-hash>")

# Verify an exact range
jovaltus_verify(before="<hash1>", after="<hash2>")

# Simplify changes since a commit
jovaltus_simplify(before="<commit-hash>")
```

No task_id needed. No pipeline state tracking.

## Running Tests During Development

```bash
# Quick: just unit tests
uv run pytest tests/ -v --ignore=tests/integration --ignore=tests/evals

# All tests including integration
uv run pytest -v --ignore=tests/evals

# Eval tests (need Docker + API keys)
EVAL_CANDIDATE_PROVIDER=deepseek \
EVAL_CANDIDATE_MODEL=deepseek/deepseek-chat \
EVAL_CANDIDATE_API_KEY=$DEEPSEEK_KEY \
EVAL_JUDGE_PROVIDER=anthropic \
EVAL_JUDGE_MODEL=anthropic/claude-sonnet-4 \
EVAL_JUDGE_API_KEY=$ANTHROPIC_KEY \
uv run pytest tests/evals/ -v -s
```

## Pre-commit Workflow

```bash
# Run all hooks manually
pre-commit run --all-files

# Run a specific hook
pre-commit run ruff --all-files
pre-commit run mypy --all-files

# Skip hooks (emergency only)
git commit --no-verify -m "..."
```

## Updating Plugin Version

1. Bump version in `pyproject.toml` `[project] version`
2. Bump version in `src/jovaltus/plugin.yaml` `version`
3. If skills changed, bump their version in respective `SKILL.md` files
4. Update release notes
5. Tag: `git tag v<version> && git push --tags` (triggers PyPI trusted publisher)

## Debugging Subagent Behavior

1. Edit prompt in `src/jovaltus/prompts/<phase>.md`
2. Restart Hermes to reload prompts (loaded at handler creation time)
3. Run pipeline with a small test task
4. Check subagent report for unexpected behavior

## How to Update

- New workflow added? → Add recipe following the pattern above
- Existing workflow changed? → Update the recipe
- Command syntax changed? → Update all recipes referencing it

## Find It Fast

```bash
grep -rn 'register_tool' src/jovaltus/__init__.py    # Where tools are registered
grep -rn 'STAGE_ORDER' src/jovaltus/                # Stage machine constants
ls src/jovaltus/prompts/                              # All subagent prompts
```
