# Phase 0: Repo scaffolding

**Status:** Implemented

**Goal:** A greenlit project skeleton that lint, type-check, and test runners all accept, with one no-op module importable.

**Tasks:**
- [x] Create `pyproject.toml` (name, version 0.1.0.dev0, deps, build backend, tool configs).
- [x] Create `src/encedo_hem/__init__.py` with a placeholder `__version__` read via `importlib.metadata`.
- [x] Create `tests/unit/test_smoke.py` with a single `import encedo_hem` assertion.
- [x] Create `.github/workflows/ci.yml` running ruff + mypy + pytest on 3.10/3.11/3.12.
- [x] Create `.gitignore` additions for `.venv/`, `dist/`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`.
- [x] `uv sync --extra dev` works locally, `uv run pytest` is green.

**Deliverable:** A green CI run on the first PR. No functionality, just a tested scaffold.

**Dependencies:** None.
