"""Eval test fixtures for Jovaltus skill evaluation.

Provides session-scoped fixtures that use fabricium's
:class:`SkillEvalHarness` to run the Jovaltus pipeline
inside a Docker container.

Environment variables
---------------------
All configuration comes from environment variables (see
:class:`fabricium.evals.EvalConfig`).  Required vars:

- ``EVAL_CANDIDATE_PROVIDER`` — e.g. ``deepseek``
- ``EVAL_CANDIDATE_MODEL`` — e.g. ``deepseek/deepseek-chat``
- ``EVAL_CANDIDATE_API_KEY``
- ``EVAL_JUDGE_PROVIDER`` — e.g. ``anthropic``
- ``EVAL_JUDGE_MODEL`` — e.g. ``anthropic/claude-sonnet-4``
- ``EVAL_JUDGE_API_KEY``
- ``EVAL_JOVALTUS_PLUGIN_DIR`` — path to the Jovaltus plugin source

Optional:
- ``EVAL_RUNS_PER_TASK`` — default 1 (bump to 3 for statistical rigour)
- ``EVAL_TASKS`` — comma-separated task ids or ``all`` (default)
- ``EVAL_KEEP`` — set ``1`` to keep container after tests
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from fabricium.evals import SkillEvalHarness
from fabricium.evals.config import EvalConfig, load_config

# ── Must be set *before* importing the config ───────────────────────

if "EVAL_JOVALTUS_PLUGIN_DIR" not in os.environ:
    os.environ["EVAL_JOVALTUS_PLUGIN_DIR"] = str(Path(__file__).parent.parent.parent)


@pytest.fixture(scope="session")
def eval_config() -> EvalConfig:
    """Load evaluation configuration from environment."""
    return load_config()


@pytest.fixture(scope="session")
def eval_harness(eval_config: EvalConfig) -> SkillEvalHarness:
    """Create and yield a harness with both profiles registered.

    The harness starts a Docker container, creates bare and
    jovaltus-agent profiles, and tears everything down after
    the session.
    """
    harness = SkillEvalHarness(eval_config)
    harness.add_profile("bare")
    harness.add_profile(
        "jovaltus-agent",
        setup_commands=["hermes jovaltus setup"],
    )
    return harness
