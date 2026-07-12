# Tech Stack — Jovaltus

| Component | Version | Category | Purpose |
|-----------|---------|----------|---------|
| Python | >=3.10 | Runtime | Plugin host language |
| fabricium | >=0.1.1 | Framework | Hermes plugin SDK — git_utils, HermesPlugin, SkillEvalHarness |
| hatchling | (build-system) | Build | PEP 621 wheel builder |
| pytest | >=8 | Testing | Test framework, 68 tests |
| ruff | >=0.8 | Lint/Format | Linting + auto-formatting |
| mypy | >=1.16 | Type Check | Strict type checking (`--strict`, zero errors) |
| pre-commit | (hooks) | CI/CD | Git hooks: ruff check → mypy → ruff format |

## Key Runtime Dep

| Dependency | Purpose |
|------------|---------|
| `fabricium.HermesPlugin` | Plugin registration: CLI commands, bundled skills |
| `fabricium.git_utils` | Git operations: diff, hash, status, stats |
| `fabricium.evals.SkillEvalHarness` | Docker-based evaluation harness for pipeline testing |

## Infrastructure (eval only)

| Component | Purpose | Config |
|-----------|---------|--------|
| Docker | Container for eval harness | `SkillEvalHarness` uses Docker |
| External LLM APIs | Candidate + judge models | `EVAL_CANDIDATE_PROVIDER` / `EVAL_JUDGE_PROVIDER` env vars |

## No Database / No HTTP Server

Jovaltus is a CLI plugin, not a web service. No database, no cache, no HTTP routes.

## How to Update

- Dependency added/removed? → Update the table and verify `pyproject.toml`
- Version bumped? → Match `pyproject.toml` `version` field and lockfile

## Find It Fast

```bash
grep -E '^requires-python|^dependencies' pyproject.toml   # Runtime requirements
grep 'dev =' pyproject.toml                                 # Dev dependencies
grep -rn 'from fabricium' src/                              # All fabricium usage
```
