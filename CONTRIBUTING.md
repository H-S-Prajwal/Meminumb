# Contributing to Meminumb

Thank you for your interest in contributing! Meminumb is a small, focused library — contributions that keep it simple and reliable are most welcome.

## Getting started

```bash
# Fork the repo on GitHub, then:
git clone https://github.com/<your-username>/Meminumb.git
cd Meminumb
pip install -e ".[dev]"
```

## Workflow

1. **Open an issue first** — describe the bug or feature before writing code. Wait for a maintainer to label it `accepted` before opening a PR.
2. **Create a branch** from `main`:
   ```bash
   git checkout -b fix/your-description
   ```
3. **Write tests** for your change. The three test files map to the three main concerns:
   - `tests/test_memory.py` — happy paths
   - `tests/test_atomicity.py` — failure + rollback scenarios
   - `tests/test_outcomes.py` — AddResult classification
4. **Run the full suite** before opening a PR:
   ```bash
   pytest tests/ -v
   ruff check meminumb/ tests/
   ```
5. **Open a PR** that references the issue (`Closes #N`). Describe what you changed and why.

## PR checklist

- [ ] Tests added or updated
- [ ] `pytest tests/ -v` passes locally
- [ ] `ruff check` passes (no lint errors)
- [ ] PR description references the linked issue

## Code style

- Python 3.10+, type hints everywhere
- `ruff` for linting (config in `pyproject.toml`)
- No external dependencies in `meminumb/` core — optional deps go in `embedder.py` behind a try/import

## Reporting bugs

Use the [bug report template](.github/ISSUE_TEMPLATE/bug_report.md). Include a minimal reproducible example.

## Good first issues

Look for issues labelled [`good first issue`](https://github.com/H-S-Prajwal/Meminumb/issues?q=label%3A%22good+first+issue%22).
