"""
ReportGenerator — produces all ProductPulse markdown reports.

Responsibility:
    Convert structured pipeline results into human-readable markdown documents.
    All metric lookups use the canonical Phase 2 metric names (snake_case).
    No analytics logic; pure string formatting.

Markdown quality rules enforced here:
    - Table separators use spaced pipes: | --- | --- |
    - Cell values are sanitised (pipes replaced, newlines stripped)
    - Date headers use plain text, not *emphasis* (avoids MD036)
    - Single blank line before --- separators (avoids MD012)
    - Metric definitions use ## category and ### metric headings

Reports generated:
    1. executive_summary.md
    2. data_quality_report.md
    3. intervention_plan.md
    4. risk_register.md
    5. metric_definitions.md
"""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)
DEFAULT_REPORTS_DIR = Path(__file__).resolve().parents[2] / "reports"
_CATEGORY_TITLES = {
    "revenue": "Revenue Metrics",
    "product": "Product Engagement Metrics",
    "customer": "Customer Health Metrics",
    "business_health_profitability": "Profitability Metrics",
    "business_health_revenue": "Revenue Health Metrics",
    "business_health_unit_economics": "Unit Economics Metrics",
    "business_health_cashflow": "Cash Flow Metrics",
    "business_health_growth": "Growth Metrics",
    "business_health_efficiency": "Efficiency Metrics",
    "business_health_risk": "Risk Metrics",
}


# ---------------------------------------------------------------------------
# Markdown helpers
# ---------------------------------------------------------------------------


def _cell(value: Any) -> str:
    """
    Sanitise a value for safe embedding in a markdown table cell.

    - Converts to string.
    - Strips leading/trailing whitespace and embedded newlines.
    - Replaces any internal pipe characters with a forward slash to prevent
      broken column counts (MD055/MD056).
    """
    text = str(value).replace("\n", " ").replace("\r", "").strip()
    return text.replace("|", "/")


def _table_row(*cells: Any) -> str:
    """Render one markdown table row with leading/trailing pipes and spaced cells."""
    return "| " + " | ".join(_cell(c) for c in cells) + " |"


def _table_separator(*widths: int) -> str:
    """Render a table separator row with spaced dashes."""
    return "| " + " | ".join("---" for _ in widths) + " |"


def _category_title(category: Any) -> str:
    """Return a readable category heading for metric glossary sections."""
    category_key = str(category or "uncategorized")
    if category_key in _CATEGORY_TITLES:
        return _CATEGORY_TITLES[category_key]
    return f"{category_key.replace('_', ' ').title()} Metrics"


def _kpi(kpis: List[Any], metric_name: str, default: float = 0.0) -> float:
    """Safely extract a KPI value by canonical metric_name."""
    return next(
        (r.value for r in kpis if r.metric_name == metric_name),
        default,
    )


def _write_report(
    filename: str,
    content: str,
    reports_dir: Path | None = None,
) -> None:
    """Write markdown content to the reports directory."""
    reports_dir = reports_dir or DEFAULT_REPORTS_DIR
    reports_dir.mkdir(parents=True, exist_ok=True)
    path = reports_dir / filename
    path.write_text(content, encoding="utf-8")
    logger.info("Generated report: %s", path)


# ---------------------------------------------------------------------------
# ReportGenerator
# ---------------------------------------------------------------------------


class ReportGenerator:
    """Generates all ProductPulse markdown reports from pipeline results."""

    def __init__(
        self,
        reports_dir: Path | None = None,
        generated_on: date | None = None,
    ) -> None:
        self.reports_dir = reports_dir or DEFAULT_REPORTS_DIR
        self.generated_on = generated_on

    # ------------------------------------------------------------------
    # Executive Summary
    # ------------------------------------------------------------------

    def generate_executive_summary(self, results: Dict[str, Any]) -> None:
        """
        Write reports/executive_summary.md using canonical Phase 2 output schemas.
        """
        generated_on = (self.generated_on or date.today()).isoformat()
        kpis = results.get("kpis", [])
        leakages = results.get("leakages", [])
        risk_profiles = results.get("risk_profiles", [])
        recommendations = results.get("recommendations", [])
        interventions = results.get("interventions", [])
        dq_scores = results.get("data_quality_scores", [])

        # Revenue KPIs
        mrr = _kpi(kpis, "monthly_recurring_revenue")
        arpu = _kpi(kpis, "average_revenue_per_user")
        grr = _kpi(kpis, "gross_revenue_retention")
        nrr = _kpi(kpis, "net_revenue_retention")
        expansion = _kpi(kpis, "expansion_revenue")
        contraction = _kpi(kpis, "contraction_revenue")
        rar = _kpi(kpis, "revenue_at_risk")

        # Customer KPIs
        churn_rate = _kpi(kpis, "customer_churn_rate")
        retention_rate = _kpi(kpis, "retention_rate")
        avg_nps = _kpi(kpis, "average_nps")

        # Product KPIs
        activation_rate = _kpi(kpis, "activation_rate")
        usage_freq = _kpi(kpis, "usage_frequency")
        key_action_rate = _kpi(kpis, "key_action_rate")
        feature_adoption = _kpi(kpis, "feature_adoption_proxy")
        engagement_drop = _kpi(kpis, "engagement_drop_rate")
        tta = _kpi(kpis, "time_to_activation")

        total_leakage = sum(
            float(leakage.get("estimated_revenue_loss", 0.0)) for leakage in leakages
        )
        leakage_types: Dict[str, float] = {}
        for leakage in leakages:
            lt = leakage.get("leakage_type", "Unknown")
            leakage_types[lt] = leakage_types.get(lt, 0.0) + float(
                leakage.get("estimated_revenue_loss", 0.0)
            )

        high_risk = [p for p in risk_profiles if p.risk_band.value in ("High", "Critical")]
        critical = [p for p in high_risk if p.risk_band.value == "Critical"]
        medium_risk = [p for p in risk_profiles if p.risk_band.value == "Medium"]
        low_risk = [p for p in risk_profiles if p.risk_band.value == "Low"]

        top_recs = recommendations[:5]

        critical_dq = [s for s in dq_scores if s.status == "Critical"]
        risk_dq = [s for s in dq_scores if s.status == "Risk"]

        # --- build table blocks ---
        snapshot_rows = "\n".join(
            [
                _table_row("Monthly Recurring Revenue (MRR)", f"${mrr:,.0f}"),
                _table_row("Average Revenue Per User (ARPU)", f"${arpu:,.2f}"),
                _table_row("Gross Revenue Retention (GRR)", f"{grr:.1%}"),
                _table_row("Net Revenue Retention (NRR)", f"{nrr:.1%}"),
                _table_row("Revenue at Risk", f"${rar:,.0f}"),
                _table_row("Customer Churn Rate", f"{churn_rate:.1%}"),
                _table_row("Customer Retention Rate", f"{retention_rate:.1%}"),
                _table_row("Average NPS", f"{avg_nps:.1f}"),
            ]
        )

        kpi_signal_rows = "\n".join(
            [
                _table_row(
                    "monthly_recurring_revenue", f"${mrr:,.0f}", "Watch" if mrr == 0 else "Active"
                ),
                _table_row(
                    "customer_churn_rate",
                    f"{churn_rate:.1%}",
                    "High" if churn_rate > 0.10 else "Acceptable",
                ),
                _table_row(
                    "gross_revenue_retention",
                    f"{grr:.1%}",
                    "Below benchmark" if grr < 0.85 else "Good",
                ),
                _table_row(
                    "net_revenue_retention",
                    f"{nrr:.1%}",
                    "Positive expansion" if nrr >= 1.0 else "Contraction",
                ),
                _table_row(
                    "average_nps",
                    f"{avg_nps:.1f}",
                    "Detractor zone" if avg_nps < 6 else "Acceptable",
                ),
            ]
        )
        risk_dist_rows = "\n".join(
            [
                _table_row("Critical", len(critical)),
                _table_row("High", len(high_risk) - len(critical)),
                _table_row("Medium", len(medium_risk)),
                _table_row("Low", len(low_risk)),
            ]
        )

        engagement_rows = "\n".join(
            [
                _table_row("Activation Rate", f"{activation_rate:.1%}"),
                _table_row("Usage Frequency (avg logins/customer)", f"{usage_freq:.1f}"),
                _table_row("Key Action Rate (actions/login)", f"{key_action_rate:.2f}"),
                _table_row("Feature Adoption Proxy (features/session)", f"{feature_adoption:.1f}"),
                _table_row("Engagement Drop Rate", f"{engagement_drop:.1%}"),
                _table_row("Time to Activation (avg days)", f"{tta:.1f}"),
            ]
        )

        leakage_rows_block = "\n".join(
            _table_row(lt, f"${amt:,.0f}")
            for lt, amt in sorted(leakage_types.items(), key=lambda x: -x[1])
        ) or _table_row("No leakage detected", "$0")

        if top_recs:
            rec_lines = "\n".join(
                f"- **{_cell(r.get('recommendation_title', 'Unnamed'))}** "
                f"(Customer: {_cell(r.get('customer_id', 'N/A'))}, "
                f"Confidence: {_cell(r.get('confidence_level', 'N/A'))}, "
                f"Owner: {_cell(r.get('suggested_owner', 'N/A'))})"
                for r in top_recs
            )
        else:
            rec_lines = "No recommendations generated."

        nrr_note = (
            "Revenue base is growing from existing customers."
            if nrr >= 1.0
            else "Contraction is outpacing expansion within the existing customer base."
        )

        top_iv_note = (
            "No prioritised interventions."
            if not interventions
            else (
                f"Highest-priority intervention: "
                f"**{_cell(interventions[0].get('recommendation_title', 'N/A'))}** "
                f"(band: {_cell(interventions[0].get('priority_band', 'N/A'))})."
            )
        )

        dq_note = (
            "No data quality scores available."
            if not dq_scores
            else f"{len(critical_dq)} dataset(s) Critical, {len(risk_dq)} dataset(s) Risk."
        )

        content = f"""# ProductPulse - Executive Analytics Summary

Generated: {generated_on}

## Related Reports

- [Data Quality Report](data_quality_report.md)
- [Intervention Plan](intervention_plan.md)
- [Risk Register](risk_register.md)
- [Metric Definitions](metric_definitions.md)

---

## 1. Executive Snapshot

| Metric | Value |
| --- | --- |
{snapshot_rows}

---

## 2. KPI Health

| KPI | Value | Signal |
| --- | --- | --- |
{kpi_signal_rows}

---

## 3. Revenue Movement

- **MRR:** ${mrr:,.0f}
- **Expansion Revenue (high-tier plans):** ${expansion:,.0f}
- **Contraction Revenue (Past Due):** ${contraction:,.0f}
- **Net Revenue Retention:** {nrr:.1%} - {nrr_note}

---

## 4. Retention and Churn

- **Churn Rate:** {churn_rate:.1%} of customers have a Canceled subscription.
- **Retention Rate:** {retention_rate:.1%} of customers are currently retained.
- **Revenue at Risk:** ${rar:,.0f} across {len(high_risk)} High/Critical risk customers.

Risk distribution:

| Band | Count |
| --- | --- |
{risk_dist_rows}

---

## 5. Product Engagement

| Metric | Value |
| --- | --- |
{engagement_rows}

---

## 6. Customer Risk Segments

{len(critical)} customer(s) are in **Critical** risk - immediate executive action required.
{len(high_risk) - len(critical)} customer(s) are in **High** risk - customer success intervention needed.
{len(medium_risk)} customer(s) are in **Medium** risk - monitor and run automated engagement.
{len(low_risk)} customer(s) are in **Low** risk - no immediate action required.

---

## 7. Revenue Leakage

Total identified leakage: **${total_leakage:,.0f}** across **{len(leakages)}** event(s).

| Leakage Type | Estimated Loss |
| --- | --- |
{leakage_rows_block}

---

## 8. Top Recommendations

{rec_lines}

---

## 9. Interventions

{len(interventions)} intervention(s) have been planned.
{top_iv_note}

See `reports/intervention_plan.md` for the full prioritised list.

---

## 10. Data Quality

{dq_note}

See `reports/data_quality_report.md` for per-dataset detail.

---

## 11. Limitations

- MRR figures are derived from the current snapshot of subscription statuses and do not represent period-over-period movement.
- Churn rate is a stock measure; period cohort churn requires prior-period snapshots.
- Revenue at risk is estimated based on active subscriptions for High/Critical risk customers only.
- NPS average is a simplified signal; true NPS = %Promoters minus %Detractors.
- Recommendations are rule-based, not ML-driven.

---

Report generated automatically by ProductPulse Analytics Engine.
"""
        _write_report("executive_summary.md", content, self.reports_dir)

    # ------------------------------------------------------------------
    # Data Quality Report
    # ------------------------------------------------------------------

    def generate_data_quality_report(self, data_quality_results: List[Any]) -> None:
        """Write reports/data_quality_report.md."""
        generated_on = (self.generated_on or date.today()).isoformat()

        if not data_quality_results:
            _write_report(
                "data_quality_report.md",
                (
                    "# Data Quality Report\n\n"
                    f"Generated: {generated_on}\n\n"
                    "## Related Reports\n\n"
                    "- [Executive Summary](executive_summary.md)\n"
                    "- [Metric Definitions](metric_definitions.md)\n\n"
                    "No data quality results available.\n"
                ),
                self.reports_dir,
            )
            return

        rows_block = "\n".join(
            _table_row(
                s.dataset,
                f"{s.completeness_score:.2%}",
                f"{s.uniqueness_score:.2%}",
                f"{s.validity_score:.2%}",
                f"{s.referential_integrity_score:.2%}",
                f"{s.overall_score:.2%}",
                s.status,
            )
            for s in data_quality_results
        )

        risk_lines = (
            "\n".join(
                f"- **{_cell(s.dataset)}** ({_cell(s.status)}): {_cell(s.business_risk)}"
                for s in data_quality_results
                if s.status in ("Risk", "Critical")
            )
            or "No datasets at risk."
        )

        content = f"""# ProductPulse - Data Quality Report

Generated: {generated_on}

## Related Reports

- [Executive Summary](executive_summary.md)
- [Metric Definitions](metric_definitions.md)

---

## Dataset Quality Scores

| Dataset | Completeness | Uniqueness | Validity | Ref. Integrity | Overall | Status |
| --- | --- | --- | --- | --- | --- | --- |
{rows_block}

---

## Risk Datasets

{risk_lines}

---

Report generated automatically by ProductPulse Analytics Engine.
"""
        _write_report("data_quality_report.md", content, self.reports_dir)

    # ------------------------------------------------------------------
    # Intervention Plan Report
    # ------------------------------------------------------------------

    def generate_intervention_plan(self, interventions: List[Dict[str, Any]]) -> None:
        """Write reports/intervention_plan.md."""
        generated_on = (self.generated_on or date.today()).isoformat()

        if not interventions:
            _write_report(
                "intervention_plan.md",
                (
                    "# Intervention Plan\n\n"
                    f"Generated: {generated_on}\n\n"
                    "## Related Reports\n\n"
                    "- [Executive Summary](executive_summary.md)\n"
                    "- [Risk Register](risk_register.md)\n\n"
                    "No interventions generated.\n"
                ),
                self.reports_dir,
            )
            return

        rows_block = "\n".join(
            _table_row(
                iv.get("intervention_id", "N/A"),
                iv.get("recommendation_title", "N/A"),
                iv.get("priority_band", "N/A"),
                iv.get("target_segment", "N/A"),
                f"${float(iv.get('estimated_revenue_impact', 0.0)):,.0f}",
                iv.get("effort_level", "N/A"),
                iv.get("suggested_owner", "N/A"),
            )
            for iv in interventions
        )

        content = f"""# ProductPulse - Intervention Plan

Generated: {generated_on}

## Related Reports

- [Executive Summary](executive_summary.md)
- [Risk Register](risk_register.md)

---

## Prioritised Interventions

| ID | Title | Priority | Segment | Revenue Impact | Effort | Owner |
| --- | --- | --- | --- | --- | --- | --- |
{rows_block}

---

Report generated automatically by ProductPulse Analytics Engine.
"""
        _write_report("intervention_plan.md", content, self.reports_dir)

    # ------------------------------------------------------------------
    # Risk Register
    # ------------------------------------------------------------------

    def generate_risk_register(self, results: Dict[str, Any]) -> None:
        """Write reports/risk_register.md."""
        generated_on = (self.generated_on or date.today()).isoformat()
        risk_profiles = results.get("risk_profiles", [])
        leakages = results.get("leakages", [])

        high_critical = [p for p in risk_profiles if p.risk_band.value in ("High", "Critical")]

        if high_critical:
            risk_rows_block = "\n".join(
                _table_row(
                    p.customer_id,
                    p.risk_band.value,
                    f"{p.risk_score:.2f}",
                    f"${p.revenue_at_risk:,.0f}",
                    "; ".join(p.drivers) if p.drivers else "N/A",
                )
                for p in sorted(high_critical, key=lambda x: -x.risk_score)
            )
        else:
            risk_rows_block = "No high/critical risk customers identified."

        if leakages:
            leakage_rows_block = "\n".join(
                _table_row(
                    leakage.get("leakage_type", "N/A"),
                    leakage.get("customer_id", "N/A"),
                    f"${float(leakage.get('estimated_revenue_loss', 0.0)):,.0f}",
                    leakage.get("recommended_action", "N/A"),
                )
                for leakage in leakages
            )
        else:
            leakage_rows_block = "No leakage events detected."

        content = f"""# ProductPulse - Risk Register

Generated: {generated_on}

## Related Reports

- [Executive Summary](executive_summary.md)
- [Intervention Plan](intervention_plan.md)

---

## High and Critical Churn Risk Customers

| Customer ID | Band | Risk Score | Revenue at Risk | Drivers |
| --- | --- | --- | --- | --- |
{risk_rows_block}

---

## Revenue Leakage Events

| Leakage Type | Customer ID | Estimated Loss | Recommended Action |
| --- | --- | --- | --- |
{leakage_rows_block}

---

Report generated automatically by ProductPulse Analytics Engine.
"""
        _write_report("risk_register.md", content, self.reports_dir)

    # ------------------------------------------------------------------
    # Metric Definitions Report
    # ------------------------------------------------------------------

    def generate_metric_definitions(self, metric_catalog: Dict[str, Any]) -> None:
        """Write reports/metric_definitions.md from the loaded metric catalog."""
        generated_on = (self.generated_on or date.today()).isoformat()
        metrics = metric_catalog.get("metrics", [])

        grouped_metrics: Dict[str, List[Dict[str, Any]]] = {}
        for metric in metrics:
            grouped_metrics.setdefault(
                str(metric.get("category", "uncategorized")),
                [],
            ).append(metric)

        category_blocks: List[str] = []
        for category, category_metrics in grouped_metrics.items():
            metric_blocks: List[str] = []
            for metric in category_metrics:
                display = _cell(metric.get("display_name", metric.get("metric_name", "Unknown")))
                block = (
                    f"### {display}\n\n"
                    f"- **ID:** `{_cell(metric.get('metric_name', 'N/A'))}`\n"
                    f"- **Category:** {_cell(metric.get('category', 'N/A'))}\n"
                    f"- **Owner:** {_cell(metric.get('business_owner', 'N/A'))}\n"
                    f"- **Grain:** {_cell(metric.get('grain', 'N/A'))}\n"
                    f"- **Formula:** {_cell(metric.get('formula_description', 'N/A'))}\n"
                    f"- **Purpose:** {_cell(metric.get('business_purpose', 'N/A'))}\n"
                    f"- **Interpretation:** {_cell(metric.get('interpretation_notes', 'N/A'))}\n"
                    f"- **Risk if misread:** {_cell(metric.get('risk_if_misread', 'N/A'))}\n"
                    f"- **Null policy:** {_cell(metric.get('allowed_null_policy', 'N/A'))}\n"
                    f"- **Enabled:** {metric.get('enabled', True)}\n"
                )
                metric_blocks.append(block)
            category_blocks.append(
                f"## {_category_title(category)}\n\n"
                + "\n\n".join(block.rstrip("\n") for block in metric_blocks)
            )

        metrics_section = (
            "\n\n---\n\n".join(category_blocks) if category_blocks else "No metrics defined."
        )

        content = f"""# ProductPulse - Metric Definitions

Generated: {generated_on}

## Related Reports

- [Executive Summary](executive_summary.md)
- [Data Quality Report](data_quality_report.md)
- [Risk Register](risk_register.md)

This document is the authoritative metric glossary for the ProductPulse analytics engine.
All formulas are implemented deterministically in Python; this document describes the
governance contract each metric must satisfy.

---

{metrics_section}

---

Report generated automatically by ProductPulse Analytics Engine.
"""
        _write_report("metric_definitions.md", content, self.reports_dir)
