---
name: jovaltus-agent
description: >-
  Orchestrates the Jovaltus 4-phase development pipeline for multi-file
  software features: Plan → Implement → Verify & Fix → Simplify. Each phase
  spawns an isolated subagent with write access, produces git commits, and
  costs significant tokens (4 subagent runs per full cycle).

  LOAD when:
  - User says "start pipeline", "enter jovaltus mode"
  - User names phases in sequence: "plan this", "implement
    and verify", "run through the pipeline"
  - User asks to "implement [feature]" where it clearly spans
    multiple files / needs reasoning (NOT a single-file fix)

  DO NOT load when:
  - Single-command investigations, typo fixes, or one-line changes
  - Quick code reviews, dependency bumps, pure read-only tasks
  - Phase words (verify/simplify/implement) appear in non-pipeline
    context (e.g., "verify the file exists", "simplify this")
  - Any task completable in under 2 minutes or in a single file

  When in doubt: do NOT load. Confirm with the user before
  committing to a 4-phase run.
author: LaiTszKin
version: 0.5.0
metadata:
  jovaltus:
    tags: [development, pipeline, code-quality, verification, multi-agent]
---

# Jovaltus Pipeline

## Goal

Drive a structured 4-phase development workflow where each phase delegates to a focused subagent.
Hooks inject stage guidance before every LLM turn so the agent never loses track of progress.
The output is a verified, simplified commit produced by the pipeline subagents.

## Acceptance Criteria

- Each phase transitions through validated stages: idle → implement → verify → simplify → done
- Stage validation rejects out-of-order tool calls with a clear error message (task_id mode)
- Commit-based mode (before/after params) bypasses stage validation for stateless operation
- Stage guidance banner appears before each LLM turn when a pipeline task is active
- Direct Delegate Pattern documented as escape hatch when in-memory state is stale

## Core Principles

- **Soft enforcement, not hard blocks.** Hooks remind the agent of the current stage; handlers validate stage transitions. The agent can always override by using the Direct Delegate Pattern.
- **One concern per subagent.** Implement writes code. Verify adversarially tests and fixes. Simplify restructures without behaviour change. No subagent does another's job.
- **Path A (subagent) by default, Path B (direct) when the context is already loaded.** The decision to delegate is a cost/quality trade-off, not a rule.

## Workflow

### Phase 0: Planning — before any tool call

1. **Clarify requirements** with `clarify` (1-3 questions per round: scope, business flow, constraints, value).
2. **Build a checklist** of structured business requirements.
3. **Research** with `web_search` if needed (API docs, package versions, known issues).
4. **Confirm** the checklist with the user.
   - **User accepts** → proceed to Phase 1.
   - **User rejects or requests changes** → loop back to step 1 (re-clarify) or step 2 (amend checklist). Do NOT proceed to Phase 1 until explicit confirmation.
   - **User cancels entirely** → stop. No task is created. Save any collected context for reference.

### Phase 1: Implement — stage: idle → implement

**Stage constraint:** No active pipeline task (stage must be idle or done).

**Pre-flight:** Check `git status --porcelain`. If the working tree has uncommitted changes, warn the user and suggest stashing or committing before proceeding. A dirty baseline corrupts the verification diff.

Choose the implementation path:

- **Path A (default) — Call `jovaltus_implement`** when the change spans multiple files, needs codebase exploration, or involves significant reasoning. The implement subagent auto-commits.
- **Path B — Implement directly** when the change is well-scoped, self-contained, mechanical, and you already hold full context. Skip the subagent but still satisfy the verification checks (tests, lint, type-check, edge-case review) before moving on.

### Phase 2: Verify & Fix — stage: implement → verify

**Stage constraint (task_id mode):** Requires stage "implement". Call `jovaltus_verify(task_id=...)`.

**Commit mode (stateless):** Pass `before=<hash>` directly. Bypasses stage validation.
Useful when:
- Task state has been lost (process restart, cross-session work)
- You manually committed changes and want to verify a specific range
- You want to iterate on the same diff multiple times

The verification subagent runs tests adversarially, reviews the diff for bugs, fixes everything found, and re-verifies until clean. It has write access and commits when done.

### Phase 3: Simplify — stage: verify → simplify

**Stage constraint (task_id mode):** Requires stage "verify". Call `jovaltus_simplify(task_id=...)`.

**Commit mode (stateless):** Pass `before=<hash>` directly. Bypasses stage validation.

The simplifier subagent applies structural improvements without behaviour change: extract repeated code, delete dead code (grep-backed), flatten nesting, improve naming. After simplification, run `pytest` (or the project's test framework) to confirm behaviour is preserved. Subagent commits when done.

### Afterwards

Present the final result: what was implemented, what issues were found and fixed during verification, what was simplified, any notable decisions. Ask if the user wants to start a new task or adjust.

## Gotchas

- **Dirty working tree corrupts the verification diff.** The pipeline records `git rev-parse HEAD` as the baseline. If the working tree has uncommitted changes before Phase 1, those changes are included in the `start_hash..HEAD` diff — the verification subagent will inspect and potentially "fix" code it didn't write. Always check `git status --porcelain` before starting Phase 1.
- **In-memory state is process-local.** Task IDs and stage tracking live in plugin memory. If the agent process restarts or you commit changes via `git` directly (not through the tools), the task state is lost and the stage becomes unknown. The hooks will stop injecting guidance. **Solution:** Use commit-based mode (`jovaltus_verify(before=<hash>)`) instead of `task_id` mode — it requires no state and works across restarts.
- **Direct Delegate Pattern (legacy escape hatch).** Before commit-based mode existed, the only way to work around stale state was to bypass the tools entirely: read the prompt file, compute the diff, and call `delegate_task` directly. **Now prefer commit-based mode** (`jovaltus_verify(before=<hash>)`) instead — it keeps the structured tool interface and is simpler. Use the Direct Delegate Pattern only when you need full control over the subagent's context (e.g., custom prompt blending).
- **Subagent crash mid-phase leaves partial changes.** If a subagent fails mid-flight, the working tree may contain incomplete edits. The pipeline does NOT auto-rollback. Manually run `git checkout -- .` or `git reset --hard HEAD` to discard partial changes before retrying. Verify with `git status` after cleanup.
- **Verify fix loop has no iteration cap.** The verification subagent retries until all checks pass. If a bug is genuinely unfixable (broken test fixture, upstream API change), the loop may diverge. If you see more than 3-4 retry cycles, intervene manually.
- **Stage validation is not a security boundary.** A determined agent can always call `delegate_task` directly. The stage machine is a productivity guide, not a guard.
- **pre_llm_call hook injects on every turn.** When a pipeline task is active, every LLM turn gets the stage banner. This keeps the agent oriented but costs a small amount of input context. To stop the injection, complete or reset the task.

## References

- `prompts/implement.md` — Implement subagent system prompt
- `prompts/verify.md` — Verification subagent system prompt (includes adversarial checklist)
- `prompts/simplify.md` — Simplifier subagent system prompt (includes simplification checklist)
- Hermes tool: `jovaltus_implement` — spawns implement subagent
- Hermes tool: `jovaltus_verify` — spawns verify subagent
- Hermes tool: `jovaltus_simplify` — spawns simplify subagent
