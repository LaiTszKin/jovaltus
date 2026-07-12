"""Integration tests for Jovaltus CLI commands in a real Hermes environment.

Jovaltus is a **single-profile** plugin (``default_profile=\"jovaltus-agent\"``).
In non-TTY (CI) mode, setup:
- Creates the ``jovaltus-agent`` profile if it doesn't exist
- Installs the bundled ``jovaltus-agent`` skill
- Applies ``SOUL.md`` to the profile directory
- Persists state to ``~/.hermes/jovaltus_state.json``

These tests run against a real Hermes agent inside Docker.
"""

from fabricium.testing.assertions import (
    CliAssert,
    assert_exit_code,
    assert_profile_in_output,
    assert_setup_completed,
    assert_skills_installed,
    assert_update_check_responded,
)
from fabricium.testing.harness import HermesDockerTestEnv

PLUGIN = "jovaltus"
PROFILE = "jovaltus-agent"


class TestJovaltusSetup:
    """``hermes jovaltus setup`` — single-profile installation."""

    def test_setup_completes_and_mentions_profile(
        self, hermes_test_env: HermesDockerTestEnv
    ) -> None:
        """First-time setup: complete successfully and mention the profile."""
        result = hermes_test_env.run_cli(PLUGIN, "setup", timeout=90)

        CliAssert.exit_code(result)
        assert_setup_completed(result, PLUGIN)
        # Jovaltus targets 'jovaltus-agent' — should appear in output
        assert_profile_in_output(result, PROFILE)

    def test_setup_installs_skills(self, hermes_test_env: HermesDockerTestEnv) -> None:
        """Setup should install the bundled jovaltus-agent skill."""
        result = hermes_test_env.run_cli(PLUGIN, "setup", timeout=90)
        CliAssert.exit_code(result)
        # Jovaltus ships with a 'jovaltus-agent' skill in skills/
        assert_skills_installed(result)

    def test_setup_is_idempotent(self, hermes_test_env: HermesDockerTestEnv) -> None:
        """Running setup multiple times should always succeed."""
        for _ in range(3):
            result = hermes_test_env.run_cli(PLUGIN, "setup", timeout=90)
            CliAssert.exit_code(result)
            assert_setup_completed(result, PLUGIN)


class TestJovaltusStatus:
    """``hermes jovaltus status`` — installation state display."""

    def test_status_works_and_shows_something(
        self, hermes_test_env: HermesDockerTestEnv
    ) -> None:
        """Status should run without error and mention the plugin."""
        result = hermes_test_env.run_cli(PLUGIN, "status")
        assert_exit_code(result)
        # Should either show profile info or a helpful "not installed" message
        assert "jovaltus" in (result.stdout + result.stderr).lower()

    def test_status_after_setup_shows_profile(
        self, hermes_test_env: HermesDockerTestEnv
    ) -> None:
        """After setup, status should show jovaltus-agent in the table."""
        hermes_test_env.run_cli(PLUGIN, "setup", timeout=90)

        result = hermes_test_env.run_cli(PLUGIN, "status")
        assert_exit_code(result)

        # The status table should at minimum contain the profile name
        assert_profile_in_output(result, PROFILE)


class TestJovaltusUpdateCheck:
    """``hermes jovaltus update --check`` — git-based update check."""

    def test_update_check_produces_diagnostic(
        self, hermes_test_env: HermesDockerTestEnv
    ) -> None:
        """Update check should produce a meaningful status message."""
        result = hermes_test_env.run_cli(PLUGIN, "update", "--check", timeout=90)
        assert_update_check_responded(result)


class TestJovaltusEdgeCases:
    """Edge cases for single-profile mode."""

    def test_unknown_command_fails(self, hermes_test_env: HermesDockerTestEnv) -> None:
        """Nonexistent subcommand should exit non-zero."""
        result = hermes_test_env.run_cli(PLUGIN, "bad-command")
        assert result.exit_code != 0

    def test_setup_output_mentions_setup(
        self, hermes_test_env: HermesDockerTestEnv
    ) -> None:
        """Setup output should be recognizable."""
        result = hermes_test_env.run_cli(PLUGIN, "setup", timeout=90)
        combined = (result.stdout + result.stderr).lower()
        assert "setup" in combined
        assert "jovaltus" in combined
