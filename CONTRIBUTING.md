# Contributing to dune-sim-py

Thanks for your interest in improving `dune-sim-py`! This document covers the
local setup and the checks your change must pass.

## Development setup

```bash
git clone https://github.com/robertruben98/dune-sim-py.git
cd dune-sim-py
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

Python 3.9+ is required. The codebase must remain 3.9-compatible, so avoid
PEP 604 (`X | None`) syntax in runtime/pydantic annotations — use
`typing.Optional` / `typing.Union`. Bare `list[...]` / `dict[...]` subscripts are
fine because every module uses `from __future__ import annotations`.

## Quality gates

All of these run in CI and must pass before a PR is merged:

```bash
ruff check .            # lint
ruff format --check .   # formatting
mypy src                # strict type-checking
pytest                  # unit tests (respx mocks, no network)
```

### Live integration tests

Integration tests are deselected by default. To run them against the real Sim
API you need a key from [sim.dune.com](https://sim.dune.com):

```bash
SIM_API_KEY=your-key pytest -m integration
```

## Workflow

1. Follow test-driven development: write a failing test, then the code to pass it.
2. Add a `Field(description=...)` to every new model field and a Google-style
   docstring to every new public function or method.
3. Update `CHANGELOG.md` under `[Unreleased]`.
4. Open a pull request against `main`.

## Building

```bash
python -m build
twine check dist/*
```
