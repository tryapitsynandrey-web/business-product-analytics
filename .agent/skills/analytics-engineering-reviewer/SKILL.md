---
name: analytics-engineering-reviewer
description: Use this skill when validating analytics logic, pandas transformations, KPI calculations, metric governance, and output correctness in ProductPulse.
---

# Analytics Engineering Reviewer Skill

## Rules

- Treat YAML as governance metadata, not executable code.
- Do not execute formulas from YAML using eval().
- Validate metrics against the metric catalog where applicable.
- Handle zero denominators safely.
- Avoid silent data loss.
- Avoid hidden assumptions in DataFrame joins.
- Prefer vectorized pandas operations over iterrows().
- Keep outputs stable and schema-aware.

## Checklist

Review:

- KPI formulas.
- Denominator safety.
- Joins.
- Null handling.
- Metric names.
- Category consistency.
- Revenue logic.
- Churn logic.
- Customer logic.
- Output schemas.
- Data quality gates.

## Required Report

Always report:

1. Analytics modules reviewed.
2. Formula risks found.
3. Schema risks found.
4. Data quality risks found.
5. Tests added or updated.
6. Remaining assumptions.
