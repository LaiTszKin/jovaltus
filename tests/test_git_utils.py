"""Tests for Jovaltus plugin — git utilities.

Uses temporary git repositories to test git operations.
"""

import subprocess
from pathlib import Path


from jovaltus import git_utils


def test_is_git_repo_true(git_repo: Path):
    assert git_utils.is_git_repo(str(git_repo)) is True


def test_is_git_repo_false(tmp_path: Path):
    assert git_utils.is_git_repo(str(tmp_path / "nonexistent")) is False


def test_get_head_hash(git_repo: Path):
    h = git_utils.get_head_hash(str(git_repo))
    assert len(h) == 40  # full SHA
    assert all(c in "0123456789abcdef" for c in h)


def test_get_diff_no_changes(git_repo: Path):
    h = git_utils.get_head_hash(str(git_repo))
    diff = git_utils.get_diff(h, "HEAD", str(git_repo))
    assert diff == ""


def test_get_diff_with_changes(git_repo: Path):
    h = git_utils.get_head_hash(str(git_repo))
    (git_repo / "file.txt").write_text("hello")
    subprocess.run(
        ["git", "add", "file.txt"], cwd=git_repo, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "commit", "-m", "add file"],
        cwd=git_repo,
        check=True,
        capture_output=True,
    )
    diff = git_utils.get_diff(h, "HEAD", str(git_repo))
    assert "hello" in diff
    assert "file.txt" in diff


def test_get_diff_stat(git_repo: Path):
    h = git_utils.get_head_hash(str(git_repo))
    (git_repo / "app.py").write_text("print('hi')\n")
    subprocess.run(
        ["git", "add", "app.py"], cwd=git_repo, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "commit", "-m", "add app"],
        cwd=git_repo,
        check=True,
        capture_output=True,
    )
    stats = git_utils.get_diff_stat(h, "HEAD", str(git_repo))
    assert len(stats) == 1
    assert stats[0]["path"] == "app.py"


def test_stage_and_commit(git_repo: Path):
    (git_repo / "new.txt").write_text("new content")
    subprocess.run(
        ["git", "add", "new.txt"], cwd=git_repo, check=True, capture_output=True
    )
    cr = git_utils.commit("test commit", str(git_repo))
    assert cr["success"] is True


def test_commit_nothing(git_repo: Path):
    """Committing with no staged changes should not raise."""
    cr = git_utils.commit("nothing", str(git_repo))
    assert cr["success"] is False  # nothing to commit


# ── Remote / Update utilities ─────────────────────────────────────


def test_get_remote_url_no_remote(git_repo: Path):
    """A repo with no remote should return empty string."""
    url = git_utils.get_remote_url(str(git_repo))
    assert url == ""


def test_get_default_branch_no_remote(git_repo: Path):
    """A repo with no remote HEAD ref should fallback to 'main'."""
    branch = git_utils.get_default_branch(str(git_repo))
    assert branch == "main"


def test_fetch_remote_no_remote(git_repo: Path):
    """Fetching with no remote should fail gracefully."""
    result = git_utils.fetch_remote(str(git_repo))
    assert result["success"] is False
    assert "message" in result


def test_get_remote_head_no_remote(git_repo: Path):
    """Getting remote HEAD with no remote should return None."""
    sha = git_utils.get_remote_head(str(git_repo))
    assert sha is None


def test_get_local_head_default(git_repo: Path):
    """get_local_head should return current HEAD by default."""
    sha = git_utils.get_local_head(str(git_repo))
    assert sha is not None
    assert len(sha) == 40


def test_get_local_head_nonexistent_branch(git_repo: Path):
    """get_local_head with a branch that doesn't exist should return None."""
    sha = git_utils.get_local_head(str(git_repo), branch="nonexistent-branch-xyz")
    assert sha is None


def test_get_ahead_behind_no_remote(git_repo: Path):
    """Ahead/behind with no remote ref should return zeros and None."""
    info = git_utils.get_ahead_behind(str(git_repo))
    assert info["ahead"] == 0
    assert info["behind"] == 0
    assert info["remote_head"] is None


def test_is_ancestor_same(git_repo: Path):
    """A commit is an ancestor of itself."""
    h = git_utils.get_head_hash(str(git_repo))
    assert git_utils.is_ancestor(h, h, str(git_repo)) is True


def test_is_ancestor_descendant(git_repo: Path):
    """An ancestor commit should be ancestor of a descendant."""
    h1 = git_utils.get_head_hash(str(git_repo))
    # Make a new commit
    (git_repo / "new.txt").write_text("content")
    subprocess.run(
        ["git", "add", "new.txt"], cwd=git_repo, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "commit", "-m", "new"], cwd=git_repo, check=True, capture_output=True
    )
    h2 = git_utils.get_head_hash(str(git_repo))
    assert git_utils.is_ancestor(h1, h2, str(git_repo)) is True


def test_is_ancestor_not(git_repo: Path):
    """A descendant should NOT be an ancestor of its ancestor."""
    h1 = git_utils.get_head_hash(str(git_repo))
    (git_repo / "other.txt").write_text("content")
    subprocess.run(
        ["git", "add", "other.txt"], cwd=git_repo, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "commit", "-m", "other"], cwd=git_repo, check=True, capture_output=True
    )
    h2 = git_utils.get_head_hash(str(git_repo))
    assert git_utils.is_ancestor(h2, h1, str(git_repo)) is False


def test_pull_branch_no_remote(git_repo: Path):
    """Pull with no remote should fail gracefully."""
    result = git_utils.pull_branch(str(git_repo))
    assert result["success"] is False
    assert "message" in result
