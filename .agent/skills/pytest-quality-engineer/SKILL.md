---
name: pytest-quality-engineer
description: Use this skill when creating, reviewing, or improving tests for ProductPulse analytics engines, validators, output contracts, and pipeline behavior.
---

# Pytest Quality Engineer Skill

## Rules

- Do not write tests that only check that a function runs.
- Avoid vacuous conditional assertions.
- Prefer deterministic in-memory fixtures.
- Do not require external services.
- Do not rely on network access.
- Test failure-first cases before happy paths.

## Required Coverage

Cover:

- Empty DataFrames.
- Missing columns.
- Zero denominators.
- Invalid values.
- Duplicate keys.
- Broken referential integrity.
- Metric calculations.
- Risk scoring.
- Recommendation rules.
- Pipeline integration.
- Output schemas.

## Required Report

Always report:

1. Tests added.
2. Tests changed.
3. Edge cases covered.
4. Weak tests found.
5. Remaining test gaps.
