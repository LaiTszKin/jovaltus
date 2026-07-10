"""Shared fixtures for Jovaltus tests."""

import subprocess
from pathlib import Path

import pytest

from jovaltus import state


@pytest.fixture(autouse=True)
def clear_task_state():
    """Reset task state before each test to avoid cross-test pollution."""
    state.clear_tasks()
    yield


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    """Create a temporary git repo with an initial commit."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    # Create an initial commit so HEAD is valid
    (repo / "README.md").write_text("# Test")
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "initial"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    return repo
