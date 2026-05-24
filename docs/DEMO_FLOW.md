# ProductPulse Demo Flow

[Back to README](../README.md)

Use this guide to review the project like a hiring manager, technical reviewer,
or stakeholder evaluating a local analytics decision engine.

## 1. Install and Verify

```bash
make setup
make ci
```

Expected result:

- Python modules compile.
- Ruff passes.
- Pyrefly reports zero errors.
- Pytest passes with the 100% coverage gate.

## Fast Path

```bash
make demo
```

Use this when the environment is already set up. It regenerates the synthetic
analytics snapshot and then opens the dashboard.

## Clean Reviewer Reset

```bash
make reset-demo
make dashboard
```

Use this when you want a known-clean local demo. The reset removes the local
SQLite dashboard database, regenerates deterministic synthetic analytics from
the configured seed, and leaves the tracked portfolio snapshots under normal
pipeline control.

## Visual Preview

Use the committed screenshots for a quick review before running the dashboard:

- [Executive Cockpit](assets/dashboard-executive-cockpit.png)
- [Top Actions](assets/dashboard-top-actions.png)
- [Customer 360](assets/dashboard-customer-360.png)
- [Scenario Simulator](assets/dashboard-scenario-simulator.png)

## Portfolio Case Study

Read [Portfolio Case Study](PORTFOLIO_CASE_STUDY.md) when you need the
reviewer narrative: problem, architecture, UX, quality gates, tradeoffs, and
evidence.

## Containerized Path

```bash
make docker-check
make docker-demo
```

Use this when you want an isolated local demo. The check validates the Compose
configuration and builds the image. The demo command then regenerates synthetic
analytics inside the container and serves the dashboard at `http://localhost:8501`.

Stop the stack with:

```bash
make docker-down
```

## 2. Generate the Analytics Snapshot

```bash
make reset-demo
```

Expected result:

- The local SQLite demo database is rebuilt from a clean state.
- Synthetic data is generated deterministically.
- Analytics engines produce KPI, churn risk, revenue leakage, recommendations,
  scenario analysis, cohort, funnel, and lineage outputs.
- CSV, SQLite, and Markdown artifacts are written locally.

## 3. Check Runtime Status

```bash
make status
```

Review:

- SQLite path points to `data/local/productpulse.db`.
- Dashboard tables are present.
- Row counts are available for KPI, Customer 360, intervention plan, decision
  traces, and advanced analytics tables.

## 4. Open the Dashboard

```bash
make dashboard
```

Review these pages in order:

1. **Executive Cockpit** - validate data freshness, business status, top
   actions, revenue leakage, and risk queues.
2. **Top Actions** - use quick views, filters, action queue, owner workload,
   chart tab, and decision brief export.
3. **Customer 360** - filter by risk, segment, and plan; inspect overview
   metrics, customer profile, recommendations, decision trace, and queue tab.
4. **Scenario Simulator** - adjust custom assumptions for churn, activation,
   ARPU, and failed-payment recovery; export custom scenario CSV.
5. **Cohort Retention** and **Funnel Analysis** - inspect retention and
   conversion views.
6. **Decision Traces** and **Metric Lineage** - verify explainability and
   governance evidence.

## 5. Inspect Generated Reports

Open:

- [Executive summary](../reports/executive_summary.md)
- [Intervention plan](../reports/intervention_plan.md)
- [Risk register](../reports/risk_register.md)
- [Metric definitions](../reports/metric_definitions.md)
- [Data quality report](../reports/data_quality_report.md)

Review:

- Recommendations have business context and priority.
- Metrics have definitions and formulas.
- Data quality output explains completeness, validity, uniqueness, and
  referential integrity.

## 6. Architecture Review

Open:

- [Architecture](ARCHITECTURE.md)
- [Generated artifacts policy](GENERATED_ARTIFACTS.md)
- [Metric catalog guide](METRIC_CATALOG.md)

Review:

- `src/core/` contains business logic only.
- `src/adapters/` owns IO and persistence boundaries.
- `app/` reads through SQLite adapter methods, not raw SQL or source CSVs.
- Generated data and reports are tracked as portfolio snapshots by policy.

## 7. Reviewer Checklist

- Local-first: no cloud service required.
- Privacy-safe: only synthetic data is used.
- Explainable: deterministic rules and decision traces, no opaque ML.
- Tested: 100% coverage gate with branch coverage.
- Governed: metrics are tied to a declarative catalog.
- Usable: dashboard supports filtering, drill-downs, exports, and scenario
  controls.
