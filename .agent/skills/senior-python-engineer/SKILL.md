---
name: senior-python-engineer
description: Use this skill when reviewing, editing, refactoring, testing, or improving Python code in the ProductPulse local-first analytics project.
---

# Senior Python Engineer Skill

## Rules

- Do not rewrite the whole project.
- Do not modify files outside the approved scope.
- Do not introduce cloud, API, ML, UI, database, or external services unless explicitly requested.
- Do not use eval().
- Do not use from src. imports.
- Keep the project compatible with PYTHONPATH=src.
- Preserve existing tests and output schemas unless explicitly asked to change them.
- Keep every file under 700 lines.
- Use type hints.
- Remove unused imports.
- Avoid dead code, placeholders, and broad refactors.

## Required Verification

Run these checks after changes:

- export PYTHONPATH=src
- python -m compileall src tests
- python -m pytest -v
- python src/main.py
- npx markdownlint-cli "reports/*.md" "README.md"
- find src tests -type f -name "*.py" -size 0 -print

## Required Report

Always report:

1. Files modified.
2. Exact changes made.
3. Test results.
4. Pipeline result.
5. Remaining risks.
6. Confirmation that no unapproved files were modified.
