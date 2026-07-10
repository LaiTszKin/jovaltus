"""Jovaltus plugin — registration entry point.

Called by Hermes at startup. Creates handler closures that capture ctx,
then registers them as tools. Also registers CLI commands and bundled skills.
"""

import logging
import os
import subprocess
from pathlib import Path

from . import schemas, git_utils
from .tools import make_implement_handler, make_verify_handler, make_simplify_handler

logger = logging.getLogger(__name__)

_PLUGIN_DIR = Path(__file__).parent


def _get_global_hermes_home() -> Path:
    """Return the global Hermes home directory, not a profile-specific one.

    When running under a profile (hermes -p jovaltus-agent), HERMES_HOME
    is set to the profile directory (e.g. ~/.hermes/profiles/jovaltus-agent/).
    We need the actual global home (~/.hermes/) for skills, profiles dir, etc.
    """
    env_home = os.environ.get("HERMES_HOME")
    if env_home:
        p = Path(env_home).resolve()
        # If we're under a profiles/<name> directory, go up two levels
        if len(p.parts) >= 2 and p.parts[-2] == "profiles":
            return p.parent.parent
        return p
    return Path.home() / ".hermes"


# ── Profile & SOUL.md ──────────────────────────────────────────────


def _get_profiles_dir() -> Path:
    """Return the global Hermes profiles directory."""
    return _get_global_hermes_home() / "profiles"


def _get_profile_dir(profile_name: str = "jovaltus-agent") -> Path:
    """Return the profile directory for jovaltus-agent."""
    return _get_profiles_dir() / profile_name


def _ensure_profile(profile_name: str = "jovaltus-agent") -> bool:
    """Create the jovaltus-agent profile if it doesn't exist.

    Returns True if the profile exists or was created.
    """
    profile_dir = _get_profile_dir(profile_name)
    if profile_dir.exists():
        return True

    print(f"Creating profile '{profile_name}'...")
    try:
        subprocess.run(
            ["hermes", "profile", "create", profile_name],
            check=True,
            capture_output=True,
            text=True,
        )
        print(f"  ✓ Profile '{profile_name}' created")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  ! Could not auto-create profile: {e.stderr.strip()}")
        print(f"    Create it manually: hermes profile create {profile_name}")
        return False
    except FileNotFoundError:
        print("  ! 'hermes' CLI not found on PATH")
        print(f"    Create the profile manually: hermes profile create {profile_name}")
        return False


def _apply_soul_md(profile_name: str = "jovaltus-agent") -> bool:
    """Write SOUL.md to the profile directory.

    The SOUL.md file sets the agent's identity as a coding agent,
    making it take on the Jovaltus coding role automatically.
    """
    profile_dir = _get_profile_dir(profile_name)
    soul_src = _PLUGIN_DIR / "SOUL.md"
    soul_dst = profile_dir / "SOUL.md"

    if not soul_src.exists():
        print(f"  ! Bundled SOUL.md not found at {soul_src}")
        return False

    try:
        soul_dst.write_text(soul_src.read_text())
        print(f"  ✓ SOUL.md written to {soul_dst}")
        return True
    except OSError as e:
        print(f"  ! Could not write SOUL.md: {e}")
        return False


def _install_bundled_skill(profile_name: str = "jovaltus-agent") -> bool:
    """Copy the bundled skill to the global skills dir so it appears in hermes skills list.

    The skill is also registered via ctx.register_skill() for namespaced
    access (skill_view("jovaltus:jovaltus-agent")). This copies it to the
    global skills directory so it also appears in 'hermes skills list'.
    Returns True if the skill was installed or already exists.
    """
    skill_name = profile_name  # "jovaltus-agent"
    skill_src = _PLUGIN_DIR / "skills" / skill_name / "SKILL.md"
    skills_dir = _get_global_hermes_home() / "skills"
    skill_dst = skills_dir / skill_name / "SKILL.md"

    if not skill_src.exists():
        print(f"  ! Bundled skill not found at {skill_src}")
        return False

    if skill_dst.exists():
        # Check if content is the same; skip if already up to date
        if skill_dst.read_text() == skill_src.read_text():
            print(f"  ✓ Skill '{skill_name}' already installed and up to date")
            return True

    try:
        skill_dst.parent.mkdir(parents=True, exist_ok=True)
        skill_dst.write_text(skill_src.read_text())
        print(f"  ✓ Skill '{skill_name}' installed to {skill_dst}")
        print("    Available in: hermes skills list")
        print(f"    Load via:     skill_view('{skill_name}')")
        return True
    except OSError as e:
        print(f"  ! Could not install skill: {e}")
        return False


# ── CLI handlers ───────────────────────────────────────────────────


def _setup_command(args) -> None:
    """Handler for 'hermes jovaltus setup'.

    Creates the jovaltus-agent profile if it doesn't exist,
    writes SOUL.md to set the coding agent role, and confirms readiness.
    """
    print("⚡ Jovaltus Setup")
    print("━" * 40)

    # Step 1: Profile
    print("\n📁 Profile")
    profile_ok = _ensure_profile()
    if profile_ok:
        print(f"  ✓ Profile '{_get_profile_dir()}' ready")

    # Step 2: SOUL.md
    print("\n🧠 Agent Identity (SOUL.md)")
    soul_ok = _apply_soul_md()
    if soul_ok:
        print("  ✓ Coding agent identity applied")
        print("    The agent will automatically adopt the Jovaltus coding role.")

    # Step 3: Bundled skill (for hermes skills list visibility)
    print("\n📚 Bundled Skill")
    skill_ok = _install_bundled_skill()
    if skill_ok:
        print("  ✓ Skill registered and installed")

    # Step 4: Summary
    print(f"\n{'━' * 40}")
    if profile_ok and soul_ok:
        print("✅ Jovaltus plugin v0.2.0 ready")
        print("  Start a session:   hermes -p jovaltus-agent")
        print("  Enable Jovaltus:   hermes tools enable jovaltus")
        print("  Run setup again:   hermes jovaltus setup")
        print("  Check for updates: hermes jovaltus update --check")
    else:
        print("⚠️  Jovaltus plugin v0.2.0 — setup incomplete")
        print("  Run again: hermes jovaltus setup")


def _update_check(args) -> None:
    """Handler for 'hermes jovaltus update --check'.

    Compares the local repository HEAD against the remote origin/main
    and reports whether updates are available.
    """
    project_dir = str(_PLUGIN_DIR.resolve())

    if not git_utils.is_git_repo(project_dir):
        print("! Not a git repository — cannot check for updates.")
        print("  If installed from a tarball or pip, re-install from source:")
        print("    git clone https://github.com/LaiTszKin/jovaltus.git")
        return

    remote_url = git_utils.get_remote_url(project_dir)
    if not remote_url:
        print("! No remote 'origin' configured — cannot check for updates.")
        return

    print("🔍 Checking for Jovaltus updates...")
    print(f"   Remote: {remote_url}")

    local_head = git_utils.get_local_head(project_dir)

    # Fetch remote refs
    print("   Fetching remote refs...", end=" ", flush=True)
    fetch_result = git_utils.fetch_remote(project_dir)
    print("✓" if fetch_result["success"] else "✗")

    if not fetch_result["success"]:
        print(f"   Fetch failed: {fetch_result['message']}")
        return

    # Compare
    info = git_utils.get_ahead_behind(project_dir)
    remote_head = info.get("remote_head")

    if remote_head is None:
        print("! Could not determine remote HEAD.")
        return

    behind = info.get("behind", 0)
    ahead = info.get("ahead", 0)

    print(f"\n   Local:  {local_head[:12] if local_head else 'unknown'}")
    print(f"   Remote: {remote_head[:12]}")

    if behind > 0:
        print(f"\n📦 {behind} new commit(s) behind remote.")
        print("   Run 'hermes jovaltus update' to pull the latest changes.")
    elif ahead > 0:
        print(f"\n⚠️  Local is {ahead} commit(s) AHEAD of remote.")
        print("   (You have local changes not yet pushed.)")
    else:
        print("\n✅ Jovaltus is up to date.")


def _update_pull(args) -> None:
    """Handler for 'hermes jovaltus update'.

    Pulls the latest changes from the remote repository.
    """
    project_dir = str(_PLUGIN_DIR.resolve())

    if not git_utils.is_git_repo(project_dir):
        print("! Not a git repository — cannot update.")
        return

    remote_url = git_utils.get_remote_url(project_dir)
    if not remote_url:
        print("! No remote 'origin' configured — cannot update.")
        return

    print("📦 Updating Jovaltus...")
    print(f"   Remote: {remote_url}")

    # Check for uncommitted changes first
    status_cmd = ["git", "-C", project_dir, "status", "--porcelain"]
    try:
        status = subprocess.check_output(status_cmd, text=True).strip()
    except subprocess.CalledProcessError:
        status = ""

    if status:
        print("\n! You have uncommitted changes. Stash or commit them first:")
        for line in status.splitlines():
            print(f"   {line}")
        print("\n  Then run: hermes jovaltus update")
        return

    # Fetch first so we can show what's coming
    print("   Fetching remote refs...", end=" ", flush=True)
    fetch_result = git_utils.fetch_remote(project_dir)
    print("✓" if fetch_result["success"] else "✗")

    if not fetch_result["success"]:
        print(f"   Fetch failed: {fetch_result['message']}")
        return

    # Check what's coming
    info = git_utils.get_ahead_behind(project_dir)
    behind = info.get("behind", 0)

    local_head = git_utils.get_local_head(project_dir)
    print(f"\n   Before: {local_head[:12] if local_head else 'unknown'}")

    if behind == 0:
        print("   After:  already up to date")
        print("\n✅ Jovaltus is already up to date.")
        return

    # Pull
    print(f"   Pulling {behind} new commit(s)...")
    result = git_utils.pull_branch(project_dir)

    if result["success"]:
        after = result.get("after", "")
        print(f"   After:  {after[:12] if after else 'unknown'}")
        print("\n✅ Jovaltus updated successfully!")
        print("   Restart any running Hermes sessions to see changes.")
    else:
        print(f"\n✗ Update failed: {result['message']}")
        print("  If the upstream force-pushed, reset with:")
        print("    git reset --hard origin/main")
        print("  (This discards local changes to Jovaltus.)")


def _jovaltus_command(args) -> None:
    """Top-level dispatcher for 'hermes jovaltus <subcommand>'."""
    sub = getattr(args, "jovaltus_command", None)

    if sub == "setup" or sub is None:
        _setup_command(args)
    elif sub == "update":
        if getattr(args, "check", False):
            _update_check(args)
        else:
            _update_pull(args)
    else:
        print(f"Unknown command: {sub}")
        print("Usage: hermes jovaltus <setup|update>")


def _setup_argparse(subparser):
    """Build argparse subcommand tree for 'hermes jovaltus'."""
    subs = subparser.add_subparsers(dest="jovaltus_command")

    # ── setup ──────────────────────────────────────────────────
    subs.add_parser(
        "setup", help="Create jovaltus-agent profile, apply SOUL.md, and verify setup"
    )

    # ── update ─────────────────────────────────────────────────
    update_parser = subs.add_parser(
        "update",
        help="Check for and apply Jovaltus plugin updates",
    )
    update_parser.add_argument(
        "--check",
        action="store_true",
        help="Only check for updates without pulling",
    )

    subparser.set_defaults(func=_jovaltus_command)


# ── Tool handler factories (called from register()) ──────────────


def register(ctx):
    """Wire schemas to handler closures, register CLI commands and skills.

    Called exactly once at Hermes startup. Each tool handler is a closure
    that captures ctx so it can call ctx.dispatch_tool("delegate_task", ...)
    to spawn subagents with the appropriate system prompts.
    """
    # ── Tools (closures capturing ctx) ───────────────────────────────
    ctx.register_tool(
        name="jovaltus_implement",
        toolset="jovaltus",
        schema=schemas.IMPLEMENT_SCHEMA,
        handler=make_implement_handler(ctx),
    )
    ctx.register_tool(
        name="jovaltus_verify",
        toolset="jovaltus",
        schema=schemas.VERIFY_SCHEMA,
        handler=make_verify_handler(ctx),
    )
    ctx.register_tool(
        name="jovaltus_simplify",
        toolset="jovaltus",
        schema=schemas.SIMPLIFY_SCHEMA,
        handler=make_simplify_handler(ctx),
    )

    # ── CLI commands ─────────────────────────────────────────────────
    ctx.register_cli_command(
        name="jovaltus",
        help="Jovaltus plugin — setup, update, and management",
        setup_fn=_setup_argparse,
        handler_fn=_jovaltus_command,
    )

    # ── Bundled skills (namespaced, read-only) ───────────────────────
    skills_dir = _PLUGIN_DIR / "skills"
    if skills_dir.is_dir():
        for child in sorted(skills_dir.iterdir()):
            skill_md = child / "SKILL.md"
            if child.is_dir() and skill_md.exists():
                ctx.register_skill(child.name, skill_md)
                logger.info("Registered bundled skill: jovaltus:%s", child.name)
