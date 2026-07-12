"""Jovaltus skill evaluation tests.

Runs the three standardised Jovaltus tasks against two profiles
(bare vs jovaltus-agent) and compares scores via LLM judge.

Requirements
------------
- Docker running
- Environment variables set (see conftest.py)
- Jovaltus plugin source available at EVAL_JOVALTUS_PLUGIN_DIR

Skip conditions
---------------
The whole module is skipped when ``EVAL_CANDIDATE_API_KEY`` is
not set (useful in CI that doesn't have Docker or API keys).
To run: set all EVAL_* env vars and invoke pytest normally.
"""

from __future__ import annotations

import os

import pytest

from fabricium.evals import EvalReport, SkillEvalHarness

from .rubrics import JOVALTUS_RUBRICS
from .tasks import JOVALTUS_TASKS

pytestmark = pytest.mark.skipif(
    not os.environ.get("EVAL_CANDIDATE_API_KEY"),
    reason="Set EVAL_CANDIDATE_API_KEY (and other EVAL_* vars) to run eval tests.",
)


class TestJovaltusSkillEval:
    """Skill evaluation: bare vs jovaltus-agent profile."""

    def test_python_backend(self, eval_harness: SkillEvalHarness) -> None:
        """Python backend task: measure Skill Lift."""
        task = [t for t in JOVALTUS_TASKS if t.id == "python-backend"][0]
        rubric = JOVALTUS_RUBRICS["python-backend"]
        report = eval_harness.run([task], rubric, runs_per_task=1)
        self._assert_lift(report, "python-backend")

    def test_typescript_frontend(self, eval_harness: SkillEvalHarness) -> None:
        """TypeScript frontend task: measure Skill Lift."""
        task = [t for t in JOVALTUS_TASKS if t.id == "typescript-frontend"][0]
        rubric = JOVALTUS_RUBRICS["typescript-frontend"]
        report = eval_harness.run([task], rubric, runs_per_task=1)
        self._assert_lift(report, "typescript-frontend")

    def test_fullstack_todo(self, eval_harness: SkillEvalHarness) -> None:
        """Fullstack todo task: measure Skill Lift."""
        task = [t for t in JOVALTUS_TASKS if t.id == "fullstack-todo"][0]
        rubric = JOVALTUS_RUBRICS["fullstack-todo"]
        report = eval_harness.run([task], rubric, runs_per_task=1)
        self._assert_lift(report, "fullstack-todo")

    def test_all_tasks(self, eval_harness: SkillEvalHarness) -> None:
        """Run all tasks and verify each produces a valid report."""
        # Use the first task's rubric for the report structure check.
        # Each task is judged with its own rubric inside the harness.
        report = eval_harness.run(JOVALTUS_TASKS, JOVALTUS_RUBRICS["python-backend"])
        assert report.task_results
        for tid, runs in report.task_results.items():
            assert len(runs) > 0, f"No runs for task {tid}"

        # Verify report serialises
        json_str = report.to_json()
        assert json_str
        assert "skill_lift" in json_str

    # ── helpers ─────────────────────────────────────────────────

    @staticmethod
    def _assert_lift(report: EvalReport, task_id: str) -> None:
        """Assert the report contains results for *task_id*."""
        assert task_id in report.task_results, (
            f"Task {task_id} not in report. Got: {list(report.task_results)}"
        )
        runs = report.task_results[task_id]
        assert len(runs) > 0, f"No runs for {task_id}"

        lift = report.skill_lift.get(task_id, {})
        assert "skill_lift" in lift, (
            f"No skill lift computed for {task_id}. Got: {lift}"
        )
        # Skill Lift should not be NaN or None
        lift_val = lift["skill_lift"]
        assert isinstance(lift_val, (int, float)), (
            f"Skill lift is not numeric: {lift_val}"
        )
