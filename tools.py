"""Tool handlers - factory functions that capture ctx and spawn subagents.

Each handler is created by a factory function in register() that captures
the Hermes plugin context (ctx). When the LLM calls the tool, the handler:

1. Validates the current pipeline stage (Layer 3)
2. Records state (git hash, task_id)
3. Reads the appropriate system prompt from prompts/*.md
4. Spawns a subagent via ctx.dispatch_tool("delegate_task", ...)
   with the prompt as the goal
5. Returns immediately (subagent runs in background)
"""

import json
import logging
from pathlib import Path

from . import state, git_utils

logger = logging.getLogger(__name__)

_PLUGIN_DIR = Path(__file__).parent
_PROMPTS_DIR = _PLUGIN_DIR / "prompts"


def _read_prompt(name: str) -> str:
    """Read a system prompt from prompts/<name>.md."""
    path = _PROMPTS_DIR / f"{name}.md"
    if path.exists():
        return path.read_text().strip()
    logger.warning("Prompt file not found: %s", path)
    return ""


def _resolve_dir(project_dir: str | None = None) -> str:
    """Resolve project directory, defaulting to cwd."""
    return str(Path(project_dir or ".").resolve())


def _spawn_review_subagent(
    ctx,
    prompt: str,
    phase_label: str,
    section_title: str,
    diff_label: str,
    subagent_label: str,
    task_id: str,
    project_dir: str,
    toolsets: list | None = None,
) -> str:
    """Shared logic for verify/simplify handlers: look up task, diff, and spawn subagent.

    All parameters are literals supplied by each handler's closure so that
    log messages, context titles, and the phase field reflect the correct phase.
    toolsets defaults to ["terminal", "file"] if not provided.
    Returns a JSON string with spawn results or error.
    """
    if toolsets is None:
        toolsets = ["terminal", "file"]

    task = state.get_task(task_id)
    if not task:
        return json.dumps(
            {
                "error": f"Task '{task_id}' not found. "
                "Did you call jovaltus_implement first?",
            }
        )

    try:
        diff_text = git_utils.get_diff(task["start_hash"], "HEAD", project_dir)
        files = git_utils.get_diff_stat(task["start_hash"], "HEAD", project_dir)

        logger.info(
            "jovaltus_%s: spawning %s subagent task=%s files=%d toolsets=%s",
            phase_label,
            subagent_label,
            task_id,
            len(files),
            toolsets,
        )

        ctx.dispatch_tool(
            "delegate_task",
            {
                "goal": prompt,
                "context": (
                    f"## {section_title}\n\n"
                    f"Working directory: {project_dir}\n"
                    f"Task: {task_id}\n"
                    f"Baseline commit: {task['start_hash']}\n"
                    f"Toolsets: {toolsets}\n"
                    f"Files changed:\n"
                    + "\n".join(
                        f"  {f['path']} (+{f['additions']}/-{f['deletions']})"
                        for f in files
                    )
                    + f"\n\n## {diff_label}\n\n```diff\n{diff_text}\n```"
                ),
                "toolsets": toolsets,
            },
        )

        return json.dumps(
            {
                "task_id": task_id,
                "start_hash": task["start_hash"],
                "diff": diff_text,
                "files_changed": files,
                "project_dir": project_dir,
                "subagent": "spawned",
                "phase": phase_label,
                "toolsets": toolsets,
            }
        )

    except Exception as e:
        logger.exception("jovaltus_%s failed", phase_label)
        return json.dumps({"error": str(e)})


# ── Factory functions (called from register()) ──────────────────────


def make_implement_handler(ctx):
    """Create jovaltus_implement handler with ctx closure."""
    prompt = _read_prompt("implement")

    def handler(args: dict, **kwargs) -> str:
        project_dir = _resolve_dir(args.get("project_dir"))

        # Stage validation: don't start implement if another task is active
        active = state.get_active_task()
        if active is not None:
            active_stage = active.get("stage", "idle")
            if active_stage not in ("idle", "done"):
                return json.dumps(
                    {
                        "error": (
                            f"Cannot start IMPLEMENT: task '{active['task_id']}' "
                            f"is in stage '{active_stage}'."
                        ),
                        "active_task": active["task_id"],
                        "current_stage": active_stage,
                        "hint": (
                            f'Continue with jovaltus_verify(task_id="{active["task_id"]}") '
                            f"or reset the task first."
                        ),
                    }
                )

        if not git_utils.is_git_repo(project_dir):
            return json.dumps(
                {
                    "error": f"Not a git repository: {project_dir}",
                    "hint": "Make sure you're in or pointing at a git repo",
                }
            )

        try:
            start_hash = git_utils.get_head_hash(project_dir)
            task_id = state.create_task(project_dir, start_hash)
            state.set_stage(task_id, "implement")
            state.set_active_task(task_id)

            logger.info(
                "jovaltus_implement: spawning implement subagent "
                "task=%s hash=%s dir=%s",
                task_id,
                start_hash,
                project_dir,
            )

            ctx.dispatch_tool(
                "delegate_task",
                {
                    "goal": prompt,
                    "context": (
                        f"## Project Context\n\n"
                        f"Working directory: {project_dir}\n"
                        f"Reference commit: {start_hash}\n"
                    ),
                    "toolsets": ["terminal", "file"],
                },
            )

            return json.dumps(
                {
                    "task_id": task_id,
                    "start_hash": start_hash,
                    "project_dir": project_dir,
                    "subagent": "spawned",
                    "phase": "implement",
                }
            )

        except Exception as e:
            logger.exception("jovaltus_implement failed")
            return json.dumps({"error": str(e)})

    return handler


def make_verify_handler(ctx):
    """Create jovaltus_verify handler with ctx closure."""
    prompt = _read_prompt("verify")

    def handler(args: dict, **kwargs) -> str:
        task_id = args.get("task_id", "")
        project_dir = _resolve_dir(args.get("project_dir"))

        # Stage validation: must be in "implement" stage
        task = state.get_task(task_id)
        if task is None:
            return json.dumps(
                {
                    "error": f"Task '{task_id}' not found.",
                    "hint": "Did you call jovaltus_implement first?",
                }
            )
        current_stage = task.get("stage", "idle")
        if current_stage != "implement":
            return json.dumps(
                {
                    "error": (
                        f"Cannot start VERIFY: task '{task_id}' "
                        f"is in stage '{current_stage}', not 'implement'."
                    ),
                    "task_id": task_id,
                    "current_stage": current_stage,
                    "expected_stage": "implement",
                }
            )
        if not state.set_stage(task_id, "verify"):
            return json.dumps(
                {"error": f"Stage transition {current_stage} \u2192 verify rejected."}
            )

        return _spawn_review_subagent(
            ctx,
            prompt,
            "verify",
            "Verification Context",
            "Git Diff",
            "verify",
            task_id,
            project_dir,
            toolsets=["terminal", "file", "computer_use"],
        )

    return handler


def make_simplify_handler(ctx):
    """Create jovaltus_simplify handler with ctx closure."""
    prompt = _read_prompt("simplify")

    def handler(args: dict, **kwargs) -> str:
        task_id = args.get("task_id", "")
        project_dir = _resolve_dir(args.get("project_dir"))

        # Stage validation: must be in "verify" stage
        task = state.get_task(task_id)
        if task is None:
            return json.dumps(
                {
                    "error": f"Task '{task_id}' not found.",
                    "hint": "Did you call jovaltus_implement first?",
                }
            )
        current_stage = task.get("stage", "idle")
        if current_stage != "verify":
            return json.dumps(
                {
                    "error": (
                        f"Cannot start SIMPLIFY: task '{task_id}' "
                        f"is in stage '{current_stage}', not 'verify'."
                    ),
                    "task_id": task_id,
                    "current_stage": current_stage,
                    "expected_stage": "verify",
                }
            )
        if not state.set_stage(task_id, "simplify"):
            return json.dumps(
                {"error": f"Stage transition {current_stage} \u2192 simplify rejected."}
            )

        return _spawn_review_subagent(
            ctx,
            prompt,
            "simplify",
            "Simplification Context",
            "Clean Diff",
            "simplifier",
            task_id,
            project_dir,
        )

    return handler
