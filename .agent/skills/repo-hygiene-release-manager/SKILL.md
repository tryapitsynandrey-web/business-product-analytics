---
name: repo-hygiene-release-manager
description: Use this skill when preparing ProductPulse for GitHub release, checking file structure, empty files, README accuracy, markdownlint, .gitignore, generated artifacts, and repository cleanliness.
---

# Repo Hygiene Release Manager Skill

## Rules

- No empty implementation files except standard __init__.py.
- No fake claims.
- No dead files.
- No unused placeholders.
- No generated junk unless intentionally included.
- README must match actual implementation.
- Markdown must pass markdownlint.
- .gitignore must reflect actual tooling.
- Do not hide broken code by ignoring it.

## Required Checks

Run:

- find src tests -type f -name "*.py" -size 0 -print
- tree -a -I ".venv|__pycache__|.pytest_cache|.git"
- npx markdownlint-cli "reports/*.md" "README.md"
- git status
- git diff --stat

## Required Report

Always report:

1. Empty files.
2. Generated artifacts status.
3. README risks.
4. Markdownlint result.
5. Git status summary.
6. Release readiness verdict.
