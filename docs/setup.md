# Setup — Jovaltus

One-shot guide to get Jovaltus running as a Hermes plugin.

## Prerequisites

| Requirement | Version | Check |
|-------------|---------|-------|
| Python | >=3.10 | `python --version` |
| uv | recent | `uv --version` |
| Hermes Agent | >=0.18.2 | `hermes --version` |
| Git | any | `git --version` |

## Install

```bash
# From PyPI (recommended)
pip install jovaltus

# Or from source
git clone https://github.com/LaiTszKin/jovaltus.git
cd jovaltus
uv pip install -e .
```

## Enable Plugin

```bash
hermes plugins enable jovaltus
```

Verify:
```bash
hermes plugins list | grep jovaltus
```

## Create Profile + Setup

```bash
hermes jovaltus setup
```

Interactive prompts (TTY detected):
- Creates `jovaltus-agent` profile if missing
- Installs bundled skills to global skills directory
- Optionally writes `SOUL.md` to profile directory
- Persists installation state to `~/.hermes/jovaltus_state.json`

Non-TTY fallback: safe defaults, no SOUL.md overwrite.

## Verify Installation

```bash
hermes jovaltus status
```

Expected output:
```
Profile: jovaltus-agent
Installation mode: pip entry point
Last updated: <timestamp>
```

## Development Setup

```bash
git clone https://github.com/LaiTszKin/jovaltus.git
cd jovaltus
uv sync                       # Install deps + dev deps
pre-commit install            # Git hooks: ruff check → mypy → ruff format
```

## Run Tests

```bash
uv run pytest -v              # 68 tests in ~3.6s
```

## Lint & Type Check

```bash
uv run ruff check .           # Zero warnings required
uv run ruff format --check .  # Format verification
uv run mypy --strict --no-site-packages *.py  # Zero errors required
```

## Environment Variables

Jovaltus itself requires no env vars. The eval harness uses:

| Variable | Required | Purpose |
|----------|----------|---------|
| `EVAL_CANDIDATE_PROVIDER` | Yes | LLM provider for candidate agent |
| `EVAL_CANDIDATE_MODEL` | Yes | Model name for candidate agent |
| `EVAL_CANDIDATE_API_KEY` | Yes | API key for candidate |
| `EVAL_JUDGE_PROVIDER` | Yes | LLM provider for judge |
| `EVAL_JUDGE_MODEL` | Yes | Model name for judge |
| `EVAL_JUDGE_API_KEY` | Yes | API key for judge |
| `EVAL_JOVALTUS_PLUGIN_DIR` | No | Path to plugin source (auto-detected) |
| `EVAL_RUNS_PER_TASK` | No | Runs per task (default 1) |
| `EVAL_TASKS` | No | Task filter (default `all`) |
| `EVAL_KEEP` | No | Keep container after tests (default off) |

## How to Update

- Prerequisites change? → Update Prerequisites table
- Install method changes? → Update install commands
- New env var added? → Add to Environment Variables table
- Setup command changes? → Update `hermes jovaltus setup` description

## Find It Fast

```bash
hermes jovaltus status       # Check installation state
hermes jovaltus update --check  # Check for updates
cat ~/.hermes/jovaltus_state.json  # Persistent state
```
