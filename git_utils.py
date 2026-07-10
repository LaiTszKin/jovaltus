"""Git subprocess wrappers for Jovaltus plugin.

All functions accept an optional repo_path parameter so they work from
any project directory. Defaults to the current working directory.
"""

import subprocess
from pathlib import Path
from typing import Optional


def _git_cmd(repo_path: Optional[str]) -> list[str]:
    """Build git -C <path> prefix when repo_path is given."""
    resolved = str(Path(repo_path or ".").resolve())
    return ["git", "-C", resolved]


def is_git_repo(repo_path: Optional[str] = None) -> bool:
    """Check if the given path is inside a git repository."""
    try:
        cmd = _git_cmd(repo_path) + ["rev-parse", "--git-dir"]
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def get_head_hash(repo_path: Optional[str] = None) -> str:
    """Return the full SHA of HEAD."""
    cmd = _git_cmd(repo_path) + ["rev-parse", "HEAD"]
    return subprocess.check_output(cmd, text=True).strip()


def get_diff(
    start_hash: str, end: str = "HEAD", repo_path: Optional[str] = None
) -> str:
    """Return the git diff between two refs as a string."""
    cmd = _git_cmd(repo_path) + ["diff", start_hash, end]
    try:
        return subprocess.check_output(cmd, text=True).strip()
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"git diff failed: {e.stderr.strip()}") from e


def get_diff_stat(
    start_hash: str, end: str = "HEAD", repo_path: Optional[str] = None
) -> list[dict]:
    """Return a list of changed files with stats.

    Each entry: {"path": str, "additions": int, "deletions": int}
    """
    cmd = _git_cmd(repo_path) + ["diff", "--numstat", start_hash, end]
    try:
        out = subprocess.check_output(cmd, text=True).strip()
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"git diff --numstat failed: {e.stderr.strip()}") from e

    if not out:
        return []
    files = []
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) == 3:
            files.append(
                {
                    "additions": int(parts[0]) if parts[0] != "-" else 0,
                    "deletions": int(parts[1]) if parts[1] != "-" else 0,
                    "path": parts[2],
                }
            )
    return files


def get_remote_url(repo_path: Optional[str] = None) -> str:
    """Return the remote origin URL. Returns empty string if no remote."""
    cmd = _git_cmd(repo_path) + ["remote", "get-url", "origin"]
    try:
        return subprocess.check_output(cmd, text=True).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def get_default_branch(repo_path: Optional[str] = None) -> str:
    """Return the default branch name (remote HEAD ref)."""
    cmd = _git_cmd(repo_path) + ["symbolic-ref", "refs/remotes/origin/HEAD"]
    try:
        out = subprocess.check_output(cmd, text=True).strip()
        return out.removeprefix("refs/remotes/origin/")
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "main"  # fallback


def fetch_remote(repo_path: Optional[str] = None) -> dict:
    """Fetch latest refs from origin. Returns {"success": bool, "message": str}."""
    cmd = _git_cmd(repo_path) + ["fetch", "--quiet", "origin"]
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=30)
        return {"success": True, "message": "Fetched remote refs"}
    except subprocess.CalledProcessError as e:
        return {"success": False, "message": e.stderr.strip() or str(e)}
    except Exception as e:
        return {"success": False, "message": str(e)}


def get_remote_head(repo_path: Optional[str] = None) -> str | None:
    """Return the latest commit SHA on remote main branch, or None.

    Requires that the remote has already been fetched.
    """
    branch = get_default_branch(repo_path)
    cmd = _git_cmd(repo_path) + ["rev-parse", f"origin/{branch}"]
    try:
        return subprocess.check_output(cmd, text=True).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def get_local_head(
    repo_path: Optional[str] = None, branch: str | None = None
) -> str | None:
    """Return the latest commit SHA on a local branch, defaulting to current HEAD."""
    ref = branch or "HEAD"
    cmd = _git_cmd(repo_path) + ["rev-parse", ref]
    try:
        return subprocess.check_output(cmd, text=True).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def get_ahead_behind(
    repo_path: Optional[str] = None, base: str = "HEAD", remote_ref: str | None = None
) -> dict:
    """Return ahead/behind counts between local and remote refs.

    Returns {"ahead": int, "behind": int, "remote_head": str | None}.
    """
    branch = get_default_branch(repo_path)
    ref = remote_ref or f"origin/{branch}"

    # First check if the remote ref exists
    cmd_check = _git_cmd(repo_path) + ["rev-parse", "--verify", ref]
    try:
        remote_sha = subprocess.check_output(cmd_check, text=True).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return {"ahead": 0, "behind": 0, "remote_head": None}

    # Count ahead/behind
    cmd = _git_cmd(repo_path) + [
        "rev-list",
        "--left-right",
        "--count",
        f"{base}...{ref}",
    ]
    try:
        out = subprocess.check_output(cmd, text=True).strip()
        parts = out.split("\t")
        ahead = int(parts[0]) if len(parts) > 0 else 0
        behind = int(parts[1]) if len(parts) > 1 else 0
        return {"ahead": ahead, "behind": behind, "remote_head": remote_sha}
    except (subprocess.CalledProcessError, FileNotFoundError):
        return {"ahead": 0, "behind": 0, "remote_head": remote_sha}


def is_ancestor(
    ancestor: str, descendant: str, repo_path: Optional[str] = None
) -> bool:
    """Check if `ancestor` is an ancestor of `descendant`.

    Returns True if ancestor == descendant (same commit).
    """
    cmd = _git_cmd(repo_path) + ["merge-base", "--is-ancestor", ancestor, descendant]
    result = subprocess.run(cmd, capture_output=True)
    return result.returncode == 0


def pull_branch(repo_path: Optional[str] = None) -> dict:
    """Pull latest changes from the tracking branch.

    Returns {"success": bool, "message": str, "before": str | None, "after": str | None}.
    """
    before = get_local_head(repo_path)
    if not before:
        return {
            "success": False,
            "message": "Could not determine current HEAD",
            "before": None,
            "after": None,
        }

    branch = get_default_branch(repo_path)
    cmd = _git_cmd(repo_path) + ["pull", "--ff-only", "origin", branch]
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=60)
        after = get_local_head(repo_path)
        return {
            "success": True,
            "message": f"Updated {branch}",
            "before": before,
            "after": after,
        }
    except subprocess.CalledProcessError as e:
        return {
            "success": False,
            "message": e.stderr.strip() or "Pull failed (not fast-forward?)",
            "before": before,
            "after": before,
        }
    except Exception as e:
        return {"success": False, "message": str(e), "before": before, "after": before}


def stage_all(repo_path: Optional[str] = None) -> None:
    """Stage all changes (git add -A)."""
    cmd = _git_cmd(repo_path) + ["add", "-A"]
    subprocess.run(cmd, check=True, capture_output=True)


def commit(message: str, repo_path: Optional[str] = None) -> dict:
    """Commit staged changes. Returns {"success": bool, "message": str}."""
    cmd = _git_cmd(repo_path) + ["commit", "-m", message]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        return {"success": True, "message": result.stdout.strip()}
    else:
        return {"success": False, "message": (result.stderr or result.stdout).strip()}
