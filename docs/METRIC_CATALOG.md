# Metric Catalog Guide

[Back to README](../README.md)

This guide is the human-readable companion to
[`config/metric_catalog.yaml`](../config/metric_catalog.yaml). The generated
glossary lives in [`reports/metric_definitions.md`](../reports/metric_definitions.md).

## Catalog Groups

| Category | Metrics | Business focus |
| --- | ---: | --- |
| `revenue` | 7 | MRR, ARPU, expansion, contraction, retention, revenue at risk |
| `product` | 5 | activation, usage, key actions, feature adoption, time to activation |
| `customer` | 5 | churn, retention, NPS, support burden, health signals |
| `business_health_profitability` | 6 | gross profit, margins, EBITDA, ROI, ROA |
| `business_health_revenue` | 3 | growth, concentration, recurring revenue health |
| `business_health_unit_economics` | 3 | CAC, LTV, LTV:CAC |
| `business_health_cashflow` | 2 | cash flow, runway |
| `business_health_growth` | 2 | customer growth, growth efficiency |
| `business_health_efficiency` | 2 | revenue per employee, sales efficiency |
| `business_health_risk` | 2 | concentration and churn exposure |

## Required Fields

Each metric entry should define:

| Field | Why it matters |
| --- | --- |
| `metric_name` | Stable machine-readable ID |
| `display_name` | Human-readable report/dashboard label |
| `category` | Glossary grouping and dashboard filtering |
| `business_owner` | Accountability for definition changes |
| `formula_description` | Explainable calculation contract |
| `source_datasets` | Lineage and validation |
| `required_columns` | Input contract |
| `business_purpose` | Why the metric exists |
| `risk_if_misread` | Governance warning |
| `enabled` | Runtime availability |

## Change Process

1. Add or update the metric in `config/metric_catalog.yaml`.
2. Map implementation status in `src/core/metric_governance.py`.
3. Implement calculation logic in `src/core/kpi_engine.py` when needed.
4. Add or update tests in `tests/test_metric_governance.py` and
   `tests/test_kpi_engine.py`.
5. Run `make ci`.
6. Regenerate reports with `make run` if the official demo snapshot should
   change.
