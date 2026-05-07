---
name: local-first-privacy-engineer
description: Use this skill when evaluating privacy, local deployment, data leakage risk, offline execution, configuration safety, or on-prem readiness in ProductPulse.
---

# Local-First Privacy Engineer Skill

## Non-Negotiable Rules

- No external API calls unless explicitly requested.
- No telemetry.
- No cloud dependency.
- No hidden network calls.
- No secrets in code.
- No real customer data in the repository.
- Synthetic data must be clearly marked.
- Configuration must not contain credentials.
- The project must run offline.

## Required Checks

Run these checks when privacy or deployment safety is relevant:

- grep -R "http|https|requests|openai|telemetry|api_key|secret" src config README.md || true
- export PYTHONPATH=src
- python src/main.py

## Required Report

Always report:

1. Privacy risks found.
2. Network dependencies found.
3. Secret-handling risks.
4. Local deployment readiness.
5. Remaining risks.
