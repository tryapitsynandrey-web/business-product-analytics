---
name: productization-architect
description: Use this skill when deciding how ProductPulse should evolve toward a local BI product, Streamlit interface, SQLite storage, metric registry, scenario simulator, and startup MVP readiness.
---

# Productization Architect Skill

## Product Direction

ProductPulse should become:

- Local-first.
- Privacy-safe.
- Explainable.
- Governance-oriented.
- Usable by analysts and business stakeholders.
- Deployable without cloud dependency.

## Rules

- Do not build UI before output contracts are stable.
- Do not add cloud, APIs, or ML before local product foundations are ready.
- Prefer SQLite before cloud databases.
- Prefer Streamlit before complex frontend stacks.
- Prefer explicit schemas before dynamic dashboards.
- Preserve CLI mode.

## Roadmap Priority

1. Output contracts.
2. Metric Registry.
3. Local storage abstraction.
4. UI-ready schemas.
5. Streamlit local UI.
6. SQLite persistence.
7. Optional connectors.
8. Packaging.

## Required Report

Always report:

1. Product impact of the proposed change.
2. Whether the change is needed now or later.
3. Risk of overengineering.
4. Local-first compatibility.
5. Recommended next phase.
