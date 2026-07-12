"""Jovaltus plugin — registration entry point.

Called by Hermes at startup. Creates handler closures that capture ctx,
then registers them as tools. Also registers CLI commands and bundled skills
via Fabricium's HermesPlugin infrastructure.
"""

import logging
import subprocess
import sys
from pathlib import Path
from typing import Any


# Self-bootstrap: fabricium must be importable before the plugin can register
# CLI commands.  Hermes manages its own venv and may recreate it during updates,
# dropping plugin-only dependencies.  This guard ensures fabricium is installed
# on first import after a Hermes update without requiring a manual pip install.
def _ensure_fabricium() -> None:
    try:
        import fabricium  # noqa: F401
    except ImportError:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", "fabricium"],
            check=True,
            capture_output=True,
        )
        # Clear stale import cache from the failed attempt above
        sys.modules.pop("fabricium", None)


_ensure_fabricium()

from fabricium import HermesPlugin  # noqa: E402

from . import hooks, schemas  # noqa: E402
from .tools import make_implement_handler, make_verify_handler, make_simplify_handler  # noqa: E402

logger = logging.getLogger(__name__)

_PLUGIN_DIR = Path(__file__).parent

plugin = HermesPlugin(
    name="jovaltus",
    plugin_dir=_PLUGIN_DIR,
    default_profile="jovaltus-agent",
)


def register(ctx: Any) -> None:
    """Wire schemas to handler closures, register CLI, skills, tools and hooks.

    Fabricium's ``plugin.register(ctx)`` handles:
    - CLI: ``hermes jovaltus setup|status|update|update --check``
    - Bundled skills from ``skills/``

    The rest is Jovaltus-unique: three pipeline tools + stage-tracking hooks.
    """
    # ── CLI + bundled skills (Fabricium) ──────────────────────────
    plugin.register(ctx)

    # ── Tools (closures capturing ctx) ────────────────────────────
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

    # ── Hooks (stage tracking & guidance) ─────────────────────────
    ctx.register_hook("post_tool_call", hooks.on_post_tool_call)
    ctx.register_hook("pre_llm_call", hooks.on_pre_llm_call)

    logger.info("Jovaltus registered (via Fabricium)")
