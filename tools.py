"""Tool handlers — factory functions that capture ctx and spawn subagents.

Each handler is created by a factory function in register() that captures
the Hermes plugin context (ctx). When the LLM calls the tool, the handler:

1. Records state (git hash, task_id)
2. Reads the appropriate system prompt from prompts/*.md
3. Spawns a subagent via ctx.dispatch_tool("delegate_task", ...)
   with the prompt as the goal
4. Returns immediately (subagent runs in background)
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
) -> str:
    """Shared logic for verify/simplify handlers: look up task, diff, and spawn subagent.

    All parameters are literals supplied by each handler's closure so that
    log messages, context titles, and the phase field reflect the correct phase.
    Returns a JSON string with spawn results or error.
    """
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
            "jovaltus_%s: spawning %s subagent task=%s files=%d",
            phase_label,
            subagent_label,
            task_id,
            len(files),
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
                    f"Files changed:\n"
                    + "\n".join(
                        f"  {f['path']} (+{f['additions']}/-{f['deletions']})"
                        for f in files
                    )
                    + f"\n\n## {diff_label}\n\n```diff\n{diff_text}\n```"
                ),
                "toolsets": ["terminal", "file"],
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
        return _spawn_review_subagent(
            ctx,
            prompt,
            "verify",
            "Verification Context",
            "Git Diff",
            "verify",
            task_id,
            project_dir,
        )

    return handler


def make_simplify_handler(ctx):
    """Create jovaltus_simplify handler with ctx closure."""
    prompt = _read_prompt("simplify")

    def handler(args: dict, **kwargs) -> str:
        task_id = args.get("task_id", "")
        project_dir = _resolve_dir(args.get("project_dir"))
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
