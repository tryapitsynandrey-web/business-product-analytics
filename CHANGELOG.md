# Changelog

[← Back to README](README.md)

All notable changes to ProductPulse are documented in this file.

## [Unreleased]

### Added

- Comprehensive edge-case and error-handling unit tests across analysis engines
- Architecture documentation with layer boundaries, data flow, and ADRs
- Human-readable metric catalog guide
- OutputSerializer for shared CSV/SQLite artifact serialization
- Typed pipeline phase result contracts
- Deterministic run stamps on tabular outputs
- 100% coverage gate in local CI
- Scenario analysis, cohort summary, funnel summary, and segment funnel output artifacts
- Dashboard pages for Scenario Simulator, Cohort Retention, and Funnel Analysis
- Data quality dashboard review page
- Decision brief summaries with Markdown exports
- Owner workload summaries for handoff queues
- Quick-view dashboard presets for filtering and sorting
- Data freshness indicators and CSV download for all dashboard tables

### Changed

- Updated project dependencies in pyproject.toml
- Moved runtime directory creation out of import-time path constants
- Standardized Streamlit imports on package import path
- Switched dependency source of truth to pyproject.toml only
- Grouped generated metric definitions by catalog category
- Added cross-links between generated Markdown reports
- Wired previously standalone cohort, funnel, and scenario engines into the main pipeline

### Fixed

- Resolved strict mypy import path validation errors in dashboard helper libraries by configuring standard source pathways in pyproject.toml
- Fixed unannotated empty set type verification errors in activation funnel calculator
- Removed redundant type-casting wrapper warnings in funnel conversion calculations
- Corrected stale test count metrics across portfolio case study documents

## [0.1.0] — 2026-05-17

### Features

- ProductPulse CLI entrypoint (`productpulse run|status|dashboard`)
- GitHub Actions CI workflow (`make ci`)
- Model contract tests and schema validation
- Makefile for all development commands
- MIT License
- Synthetic data engine with seeded reproducibility
- Analytics engines: KPI, Churn Risk, Revenue Leakage, Recommendations
- Metric Governance Engine with YAML-driven catalog
- Business Health Score Engine (7 domain scorers)
- Customer 360 composite view
- Intervention Planner with priority scoring
- Decision Trace Engine for explainability
- Data Quality Scorer
- SQLite persistence layer (writer + read-only reader)
- Streamlit dashboard with 11 navigation pages
- Markdown report generation (executive summary, metric definitions, risk register)
- Generated artifacts Git policy documentation

### Infrastructure

- Python 3.10+ with Pandas, NumPy, PyYAML, Streamlit
- Ruff linting, Pyrefly type checking, pytest with coverage gate
- Editable install via `pip install -e ".[dev]"`

## [0.0.1] — 2026-02-20

- Initial commit
