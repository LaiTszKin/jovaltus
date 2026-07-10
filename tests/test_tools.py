"""Tests for Jovaltus plugin — tool handlers.

Uses mocked ctx to verify handler behaviour
without a live Hermes runtime.
"""

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from jovaltus.tools import (
    make_implement_handler,
    make_verify_handler,
    make_simplify_handler,
)


@pytest.fixture
def ctx() -> MagicMock:
    return MagicMock()


# ── jovaltus_implement ────────────────────────────────────────────


def test_implement_not_git_dir(ctx: MagicMock):
    """Non-git directory should return an error."""
    handler = make_implement_handler(ctx)
    result = json.loads(handler({"project_dir": "/tmp/nonexistent-12345"}))
    assert "error" in result
    assert "git" in result["error"].lower()


def test_implement_success(ctx: MagicMock, git_repo: Path):
    """Happy path: creates task and dispatches subagent."""
    handler = make_implement_handler(ctx)
    result = json.loads(handler({"project_dir": str(git_repo)}))

    assert "task_id" in result
    assert "start_hash" in result
    assert len(result["start_hash"]) == 40
    assert result["subagent"] == "spawned"
    assert result["phase"] == "implement"

    # Should have called dispatch_tool once
    assert ctx.dispatch_tool.call_count == 1
    call_args = ctx.dispatch_tool.call_args[0]
    assert call_args[0] == "delegate_task"
    assert "goal" in call_args[1]
    assert "implement" in call_args[1]["goal"].lower()


# ── jovaltus_verify ───────────────────────────────────────────────


def test_verify_no_task_id(ctx: MagicMock):
    handler = make_verify_handler(ctx)
    result = json.loads(handler({"task_id": "nonexistent"}))
    assert "error" in result


def test_verify_success(ctx: MagicMock, git_repo: Path):
    """Verify handler should compute diff and dispatch."""
    # Create a task first via implement handler
    impl_handler = make_implement_handler(ctx)
    ctx.reset_mock()
    impl_result = json.loads(impl_handler({"project_dir": str(git_repo)}))
    task_id = impl_result["task_id"]

    # Make a change so there's something to diff
    (git_repo / "file.py").write_text("x = 1")
    subprocess.run(
        ["git", "add", "file.py"], cwd=git_repo, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "commit", "-m", "add file"],
        cwd=git_repo,
        check=True,
        capture_output=True,
    )

    ctx.reset_mock()
    verify_handler = make_verify_handler(ctx)
    result = json.loads(
        verify_handler({"task_id": task_id, "project_dir": str(git_repo)})
    )

    assert result["subagent"] == "spawned"
    assert result["phase"] == "verify"
    assert "diff" in result
    assert "file.py" in result["diff"] or result["files_changed"]
    assert ctx.dispatch_tool.called


# ── jovaltus_simplify ─────────────────────────────────────────────


def test_simplify_no_task_id(ctx: MagicMock):
    handler = make_simplify_handler(ctx)
    result = json.loads(handler({"task_id": "nonexistent"}))
    assert "error" in result


def test_simplify_success(ctx: MagicMock, git_repo: Path):
    """Simplify handler should compute clean diff and dispatch."""
    impl_handler = make_implement_handler(ctx)
    ctx.reset_mock()
    impl_result = json.loads(impl_handler({"project_dir": str(git_repo)}))
    task_id = impl_result["task_id"]

    (git_repo / "app.py").write_text("print(1)\n")
    subprocess.run(
        ["git", "add", "app.py"], cwd=git_repo, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "commit", "-m", "add app"],
        cwd=git_repo,
        check=True,
        capture_output=True,
    )

    ctx.reset_mock()
    simplify_handler = make_simplify_handler(ctx)
    result = json.loads(
        simplify_handler({"task_id": task_id, "project_dir": str(git_repo)})
    )

    assert result["subagent"] == "spawned"
    assert result["phase"] == "simplify"
    assert ctx.dispatch_tool.called


# ── Prompt files exist ────────────────────────────────────────────


def test_prompt_files_exist():
    """The three prompt files should be present and non-empty."""
    base = Path(__file__).parent.parent / "prompts"
    for name in ["implement", "verify", "simplify"]:
        path = base / f"{name}.md"
        assert path.exists(), f"Missing prompt: {path}"
        assert path.read_text().strip(), f"Empty prompt: {path}"
