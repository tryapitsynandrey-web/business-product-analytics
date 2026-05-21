# Release Checklist

[← Back to README](README.md)

Before tagging a new release or merging a major feature, run the following verification steps:

## 1. Environment Verification

```bash
source .venv/bin/activate
export PYTHONPATH=src:.
```

## 2. Empty File & Temporary Artifact Check

```bash
find src tests app -type f -name "*.py" -size 0 -print
find . -maxdepth 3 -type f \( -name "*.tmp" -o -name "*.log" -o -name ".DS_Store" \) -print
```

*Ensure no empty files or unignored temporaries exist.*

## 3. Forbidden Logic Check

```bash
grep -R "from src\." src tests app
grep -R "eval(" src tests app
grep -R "pd.read_csv\|read_csv" app
grep -R "SELECT\|INSERT\|UPDATE\|DELETE\|DROP\|CREATE" app
```

*Ensure the UI does not bypass the adapter layer or use raw queries.*

## 4. Privacy & Dependency Check

```bash
grep -R "requests\|httpx\|urllib\|openai\|api_key\|secret\|telemetry" src config app README.md
grep -R "plotly\|altair\|dash" app pyproject.toml README.md
```

*Ensure no external network calls or heavy UI dependencies have crept in.*

## 5. Automated Tests

```bash
make ci
```

*Ensure 100% test pass rate and current 100% coverage.*

## 6. End-to-End Pipeline

```bash
make run
```

*Verify successful synthetic data generation and artifact creation.*

## 7. Markdown Linting

```bash
npx markdownlint-cli "reports/*.md" "README.md" "*.md"
```

*Ensure clean documentation formatting.*

## 8. Dashboard Manual Check

```bash
make dashboard
```

*Click through all sidebar tabs and interact with filters.*

## 9. Portfolio Demo Flow

```bash
sed -n '1,220p' docs/DEMO_FLOW.md
```

*Walk through the reviewer path and confirm the README, reports, dashboard,
and architecture links still match the current project state.*

## 10. Git Status

```bash
git status --short
git diff --stat
```

*Ensure a clean working tree.*

**Note on Generated Artifacts:**
Running the pipeline generates large diffs in `data/` and `reports/`.
These files are intentionally tracked as portfolio demos. Do not commit
these diffs unless you intend to update the official snapshot.
See `docs/GENERATED_ARTIFACTS.md` for policy details.
