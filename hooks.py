"""Jovaltus hooks — stage tracking and guidance injection.

Two hooks work together to guide the main agent through the pipeline:

1. post_tool_call: Detects when a Jovaltus tool returns, records
   the stage transition, and sets the active task.

2. pre_llm_call: Before each LLM turn, injects context reminding the
   agent what stage it's in and what to do next.

This implements the "soft enforcement / adaptive nudge" pattern:
the agent always knows its stage, but is never forced.
"""

import json
import logging
from typing import Any

from . import state

logger = logging.getLogger(__name__)

# ── Stage labels for user-facing guidance ─────────────────────────

_STAGE_LABELS: dict[str, str] = {
    "idle": "⏸️  Idle",
    "implement": "🔧 Implement",
    "verify": "🔍 Verify & Fix",
    "simplify": "🧹 Simplify",
    "done": "✅ Complete",
}

_STAGE_HINTS: dict[str, list[str]] = {
    "idle": [
        "Ready to start a new task.",
        "Call `jovaltus_implement(project_dir=...)` to begin.",
    ],
    "implement": [
        "Implement subagent is running — wait for its report.",
        "When it finishes, review the changes, then call `jovaltus_verify(task_id=...)`.",
    ],
    "verify": [
        "Verification subagent is running the Three-Layer Protocol:",
        "  Layer 1 — Static: tests, lint, type check, diff review (fastest, run first)",
        "  Layer 2 — Behavior: start dev server, interact (computer_use or curl), test edge cases",
        "  Layer 3 — Logs: capture runtime logs, grep for ERROR/Traceback/5xx, correlate with behavior",
        "The subagent produces a COMPOSITE VERIFICATION REPORT at the end.",
        "Read the report — only proceed if verdict is ALL-PASS.",
        "Call `jovaltus_simplify(task_id=...)` when ready for the next phase.",
    ],
    "simplify": [
        "Simplify subagent is running — wait for its report.",
        "Pipeline completion is next.",
    ],
    "done": [
        "Pipeline complete! All stages finished successfully.",
        "Start a new task with `jovaltus_implement()`.",
    ],
}


def _build_stage_banner(task: dict) -> str:
    """Build the stage guidance banner injected into pre_llm_call."""
    tid = task.get("task_id", "?")
    stage = task.get("stage", "idle")
    label = _STAGE_LABELS.get(stage, stage)
    hints = _STAGE_HINTS.get(stage, [])

    # Build pipeline progress bar
    bar_parts: list[str] = []
    stage_index = state.STAGE_ORDER.index(stage)
    for idx, s in enumerate(state.STAGE_ORDER):
        if s == "idle":
            continue
        if s == stage:
            bar_parts.append(f"**{s}** ← active")
        elif idx < stage_index:
            bar_parts.append(f"~~{s}~~ ✓")
        else:
            bar_parts.append(s)

    bar = " → ".join(bar_parts)

    lines = [
        f"## 📋 Jovaltus Pipeline — {label}",
        "",
        f"**Task:** `{tid}`",
        f"**Stage:** `{stage}`",
        f"**Progress:** {bar}",
        "",
        "**Guidance:**",
    ]
    for hint in hints:
        lines.append(f"- {hint}")

    return "\n".join(lines)


# ── Hooks ──────────────────────────────────────────────────────────


def on_post_tool_call(
    tool_name: str,
    args: dict[str, Any],
    result: str,
    task_id: str,
    **kwargs: Any,
) -> None:
    """PostToolUse hook — detect Jovaltus tool returns and update stage.

    Fires after every tool call. Only acts on jovaltus_implement,
    jovaltus_verify, and jovaltus_simplify.
    """
    if tool_name not in ("jovaltus_implement", "jovaltus_verify", "jovaltus_simplify"):
        return

    logger.debug("jovaltus post_tool_call: tool=%s task_id=%s", tool_name, task_id)

    # Parse the result to extract the pipeline task_id
    try:
        data = json.loads(result)
    except (json.JSONDecodeError, TypeError):
        logger.warning("jovaltus: could not parse result JSON for %s", tool_name)
        return

    pipeline_task_id = data.get("task_id", "")
    if not pipeline_task_id:
        logger.warning("jovaltus: no pipeline task_id in %s result", tool_name)
        return

    phase = data.get("phase", "")
    # tool_name is always one of the three (guarded above); fallback to phase
    _stage_of_tool = {
        "jovaltus_implement": "implement",
        "jovaltus_verify": "verify",
        "jovaltus_simplify": "simplify",
    }
    target_stage = _stage_of_tool.get(tool_name, phase)

    if target_stage:
        ok = state.set_stage(pipeline_task_id, target_stage)
        if ok:
            state.set_active_task(pipeline_task_id)
            logger.info(
                "jovaltus: stage transition task=%s → %s",
                pipeline_task_id,
                target_stage,
            )
        else:
            current = state.get_stage(pipeline_task_id)
            logger.warning(
                "jovaltus: rejected stage transition task=%s current=%s → %s",
                pipeline_task_id,
                current,
                target_stage,
            )


def on_pre_llm_call(
    session_id: str,
    user_message: str,
    **kwargs: Any,
) -> dict | None:
    """PreLLMCall hook — inject stage guidance context.

    Fires before every LLM turn. If there's an active Jovaltus task,
    injects a banner reminding the agent of the current stage and
    what to do next.
    """
    task = state.get_active_task()
    if task is None:
        return None

    stage = task.get("stage", "idle")
    banner = _build_stage_banner(task)

    logger.debug(
        "jovaltus pre_llm_call: injecting stage=%s task=%s",
        stage,
        task.get("task_id", "?"),
    )
    return {"context": banner}
