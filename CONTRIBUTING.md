# Contributing to ProductPulse

[← Back to README](README.md)

Thank you for considering contributing to ProductPulse.

## Development Setup

```bash
git clone https://github.com/tryapitsynandrey-web/business-product-analytics.git
cd business-product-analytics
python3 -m venv .venv
source .venv/bin/activate
make setup
```

## Running the CI Suite

Before submitting any changes, run the full local CI:

```bash
make ci
```

This runs compile checks, Ruff linting, Pyrefly type checking, and the
full pytest suite with 100% coverage enforcement.

## Architecture Boundaries

- **`src/adapters/`** — IO only (CSV, SQLite, synthetic data). No business logic.
- **`src/core/`** — Analytics engines. No filesystem or database access.
- **`src/models/`** — Data contracts (dataclasses, schemas). Zero logic.
- **`src/utils/`** — Cross-cutting concerns (paths, validation, logging).
- **`app/`** — Streamlit dashboard. Reads from SQLite via `SQLiteReader` only.

Do not import `adapters` from `core/` (except in `pipeline.py`).
Do not add direct SQL queries in `app/`.
Use `OutputSerializer` for new CSV/SQLite output artifacts instead of adding
duplicate serialization blocks to the pipeline.

## Adding a New Metric

1. Register the metric in `config/metric_catalog.yaml` with ownership and formula.
2. Map the implementation key in `src/core/metric_governance.py` `IMPLEMENTATION_MAP`.
3. Implement the calculation method in `src/core/kpi_engine.py`.
4. Add the output columns to `src/models/schemas.py` `OUTPUT_SCHEMAS`.
5. Write tests in `tests/`.

## Commit Guidelines

- Keep commits focused on a single change.
- Do not commit changes to `data/` or `reports/` unless updating the official
  demo snapshot (see [docs/GENERATED_ARTIFACTS.md](docs/GENERATED_ARTIFACTS.md)).

## Code Style

- Ruff handles formatting and linting (`make format`, `make lint`).
- Pyrefly handles type checking (`make typecheck`).
- All new code should include type annotations.

## Reporting Issues

Open an issue on GitHub with a clear description, expected behavior, and
steps to reproduce.
