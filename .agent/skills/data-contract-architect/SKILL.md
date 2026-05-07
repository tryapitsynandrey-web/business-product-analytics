---
name: data-contract-architect
description: Use this skill when working on CSV outputs, schema validation, UI-ready data contracts, generated artifacts, and stable local BI interfaces.
---

# Data Contract Architect Skill

## Rules

- Do not change output schemas without explicit approval.
- Prefer additive fields over breaking changes.
- Required columns must be explicit.
- Extra columns may be allowed for forward compatibility.
- Do not drop data silently.
- Do not manually edit generated data files unless explicitly requested.
- Generated artifacts must be reproducible through the pipeline.

## Output Contracts

Protect these artifacts:

- data/processed/kpi_summary.csv
- data/processed/customer_360.csv
- data/processed/data_quality_scores.csv
- data/processed/intervention_plan.csv
- data/processed/health_scores.csv
- data/exports/churn_risk_profiles.csv
- data/exports/revenue_leakage.csv
- data/exports/recommendations.csv
- data/exports/decision_traces.csv
- data/exports/metric_lineage.csv

## Required Report

Always report:

1. Output schemas touched.
2. Artifacts generated.
3. Contract changes.
4. Backward compatibility risks.
5. UI readiness impact.
