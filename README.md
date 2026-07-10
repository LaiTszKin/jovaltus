# Jovaltus — Hermes Plugin for Agent Mode

> **Jovaltus** is a Hermes Agent plugin that transforms the main agent into an intelligent development orchestrator. Designed for quick bug fixes and small-to-medium features, it provides a structured four-phase pipeline — Plan → Implement → Verify & Fix → Simplify — while keeping the workflow invisible to the user.

---

## Overview

Jovaltus takes a single user request and runs it through an automated quality pipeline. The user only participates in Phase 0 (requirement clarification). Everything else — implementation, adversarial verification, code simplification — is handled autonomously by subagents.

```
User Request
    │
    ├── Phase 0: Planning (Main Agent)
    │   Round-based clarification → Checklist → User confirmation
    │
    ├── Phase 1: Implement (Subagent)
    │   Writes code. Reports BLOCKED if stuck.
    │
    ├── Phase 2: Verify & Fix (Subagent)
    │   Adversarial testing. Finds problems, fixes them, repeats until clean.
    │
    └── Phase 3: Simplify (Subagent)
        Structural cleanup. No behaviour changes.
```

---

## Architecture

### Three-Layer Design

| Layer | What It Does | Why |
|-------|-------------|-----|
| **Skill** (documents) | Describes what each phase should do. No tool names. | LLM reads this + tool schemas, figures out the flow itself. |
| **Tool Handler** (thin Python) | Tracks state, stores git hashes, computes diffs. Returns JSON to the main agent. | Keeps state management away from the LLM. Main agent decides the orchestration. |
| **Hook** (mechanical Python) | `pre_tool_call`: records git hash before implement. `post_tool_call`: auto-commits after implement. | Pure automation. No LLM involved. |

### The Main Agent as Orchestrator

The main agent (the conversation partner) serves as the **planner and dispatcher**:

1. Follow the Skill document to understand what phase comes next
2. Call the Jovaltus plugin tool (e.g. `jovaltus_implement`) to get state context
3. Read the tool's response — `task_id`, `start_hash`, etc.
4. Call `delegate_task` with the right goal, context, and toolsets to spawn a subagent
5. Read the subagent's summary and decide the next phase

The plugin tools never call `delegate_task` themselves. They are state keepers, not dispatchers. The main agent owns the orchestration.

---

## The Four Phases

### Phase 0: Planning (Main Agent)

The only phase the user interacts with.

```
User: "Build a login page"
    │
    ├── Step 1: Round-based clarification (1-3 questions per round, multiple choice)
    │   Scope → Business flow → Constraints → Business value
    │
    ├── Step 2: Decompose into a business requirement checklist
    │
    ├── Step 3: Web search for latest information (avoids knowledge cut-off)
    │
    └── Step 4: User confirms the plan
        "Don't start implementing until the user says yes."
```

### Phase 1: Implement (Subagent)

```
Main agent calls jovaltus_implement
    → Handler records start_hash, returns {task_id, start_hash}

Main agent calls delegate_task(goal=..., context=..., toolsets=[terminal, file])
    → Subagent:
        • Reads context from tool handler
        • Writes code (full read/write access)
        • Does NOT verify, does NOT simplify
        • Reports BLOCKED if genuinely stuck

Hook: post_tool_call detects jovaltus_implement → auto git commit
```

**Tool permissions**: `terminal`, `file` (full read/write).  
**Red lines**: ❌ No touching irrelevant files. ❌ No self-verification. ❌ No self-simplification.

### Phase 2: Verify & Fix (Subagent)

```
Main agent calls jovaltus_verify
    → Handler computes git diff (start_hash → HEAD), returns diff context

Main agent calls delegate_task(goal=adversarial verification, context=diff, toolsets=[terminal, file])
    → Subagent (with write access):
        • Runs the code
        • Tries to break it (adversarial mindset)
        • Finds bugs → fixes them directly → commits → re-verifies
        • Loops until all tests pass (self-contained verify-fix loop)
        • Reports what was found and fixed
```

**Mindset**: Adversarial. Not "does it work?" but "how can I break this?"  
**Write access**: The subagent can fix what it finds — no read-only reporting. This is the Fable 5 closed-loop model.

### Phase 3: Simplify (Subagent)

```
Main agent calls jovaltus_simplify
    → Handler computes clean diff (start_hash → HEAD, no intermediate fix commits)

Main agent calls delegate_task(goal=structural simplification, context=clean diff, toolsets=[terminal, file])
    → Subagent:
        • No behaviour changes
        • Structural priorities: extract duplicates > delete dead code > flatten nesting > improve naming
        • Mandatory grep evidence before deleting anything
        • Reports simplification summary
```

**Value hierarchy**: Extract duplicates → Delete dead code → Flatten nesting → Improve naming.  
**Safety**: Every deletion requires grep evidence. Behaviour must be strictly preserved.

---

## Installation and Usage

### Install

```bash
# From GitHub
hermes plugins install LaiTszKin/jovaltus --enable

# Run setup to create the jovaltus-agent profile
hermes jovaltus setup
```

### Daily Use

```bash
# Start a session in Agent Mode
hermes -p jovaltus-agent

# Works in any project directory — profile is not directory-bound
cd /projects/app-alpha
hermes -p jovaltus-agent

cd /projects/app-beta
hermes -p jovaltus-agent
```

---

## Plugin File Structure

```
~/.hermes/plugins/jovaltus/
├── plugin.yaml              # Manifest
├── __init__.py              # register() — mounts tools, hooks, CLI commands, skills
├── hooks.py                 # pre/post tool_call: git hash tracking, auto-commit
├── tools.py                 # Thin handlers: state management, diff computation
├── state.py                 # Task state (in-memory dict)
├── git_utils.py             # Git subprocess wrappers
│
├── skills/
│   └── jovaltus-agent/
│       └── SKILL.md         # Agent Mode workflow (no tool names)
│
└── prompts/
    ├── implement.md         # Implement agent system prompt
    ├── verify.md            # Verification agent system prompt
    └── simplify.md          # Simplifier agent system prompt
```

---

## Technical Decisions

| Aspect | Decision |
|--------|----------|
| **Profile** | `jovaltus-agent`, separate from any other mode |
| **Plugin sharing** | GitHub repo + `hermes plugins install` |
| **Profile init** | Plugin provides `hermes jovaltus setup` CLI command (`ctx.register_cli_command`) |
| **Profile binding** | Not directory-bound — same profile works across projects |
| **Pipeline control** | Skill document guides main agent, no orchestrator code |
| **Git tracking** | Hooks handle pre/post implement automatically |
| **Task ID flow** | Plugin tool returns `task_id` → main agent reads it → passes to next tool |
| **Diff computation** | `git diff <start-hash> HEAD` handled by the plugin tool |
| **Verify loop** | Verification subagent has write access and runs a self-contained `verify → fix → re-verify` loop |
| **Simplify input** | Clean diff (start vs final, no intermediate fix commits) |
| **Skill style** | Describes *what* to do, never names tools |
| **Plugin skills** | Read-only, namespaced (`"jovaltus-agent:jovaltus-agent"`), loaded via `skill_view()` |
| **Tool handler** | State manager only — returns JSON, does not dispatch `delegate_task` |

---

## Design Principles

### Why Three Layers?

- **Skill** = what the LLM reads to know the workflow. Changes with the model's reading comprehension.
- **Tool Handler** = what Python runs to manage state. Changes when the data model changes.
- **Hook** = pure mechanical automation. Changes when the git workflow changes.

Separate concerns means changing the workflow (e.g. adding a new phase) only requires updating the Skill document — no Python code changes.

### Why the Main Agent Orchestrates?

The main agent has access to the full tool set (`delegate_task`, `web_search`, `skill_view`, etc.) and full conversational context. Putting orchestration logic in Python would:
- Lose access to `delegate_task` (tool handlers can't call it)
- Require maintaining a second planning layer in code
- Fight against the LLM's natural strength at reasoning about workflows

### Why Adversarial Verification?

Testing to confirm "it works" misses edge cases. Testing to "break it" surfaces:
- Input sanitisation gaps (XSS, injection)
- Rate limiting failures
- Incorrect error handling
- State management bugs

The verification subagent has write access so it can fix what it finds — no read-only reporting that creates more work for the main agent.

---

## License

MIT
