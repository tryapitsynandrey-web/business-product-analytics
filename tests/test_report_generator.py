from __future__ import annotations

from datetime import date
from types import SimpleNamespace

from core.report_generator import ReportGenerator, _table_separator
from models.enums import RiskBand


def _kpi(metric_name: str, value: float):
    return SimpleNamespace(
        metric_name=metric_name,
        value=value,
        grain="overall",
        explanation=f"{metric_name} explanation",
    )


def _risk_profile():
    return SimpleNamespace(
        customer_id="C1",
        risk_score=0.91,
        risk_band=RiskBand.CRITICAL,
        drivers=["usage | drop", "failed payment"],
        revenue_at_risk=1_250.0,
        explanation="Critical risk",
    )


def _data_quality_score():
    return SimpleNamespace(
        dataset="customers|raw",
        completeness_score=0.95,
        uniqueness_score=1.0,
        validity_score=0.9,
        referential_integrity_score=0.85,
        overall_score=0.92,
        status="Risk",
        business_risk="billing | join risk\nwith newline",
    )


def test_report_generator_writes_all_reports_and_sanitizes_table_cells(tmp_path):
    generator = ReportGenerator(
        reports_dir=tmp_path,
        generated_on=date(2026, 5, 1),
    )
    results = {
        "kpis": [
            _kpi("monthly_recurring_revenue", 10_000.0),
            _kpi("average_revenue_per_user", 250.0),
            _kpi("gross_revenue_retention", 0.88),
            _kpi("net_revenue_retention", 1.05),
            _kpi("customer_churn_rate", 0.08),
            _kpi("average_nps", 7.4),
            _kpi("revenue_at_risk", 1_250.0),
        ],
        "leakages": [
            {
                "leakage_type": "Failed | Payment",
                "customer_id": "C1",
                "estimated_revenue_loss": 250.0,
                "recommended_action": "Retry\nnow",
            }
        ],
        "risk_profiles": [_risk_profile()],
        "recommendations": [
            {
                "recommendation_title": "Fix | Billing",
                "customer_id": "C1\nnext",
                "confidence_level": "High",
                "suggested_owner": "Finance",
            }
        ],
        "interventions": [
            {
                "intervention_id": "INT-1",
                "recommendation_title": "Fix | Billing",
                "priority_band": "High",
                "target_segment": "SMB",
                "estimated_revenue_impact": 250.0,
                "effort_level": "Low",
                "suggested_owner": "Finance",
            }
        ],
        "data_quality_scores": [_data_quality_score()],
    }

    generator.generate_executive_summary(results)
    generator.generate_data_quality_report(results["data_quality_scores"])
    generator.generate_intervention_plan(results["interventions"])
    generator.generate_risk_register(results)
    generator.generate_metric_definitions(
        {
            "metrics": [
                {
                    "metric_name": "monthly_recurring_revenue",
                    "display_name": "MRR | Current",
                    "category": "revenue",
                    "business_owner": "Finance",
                    "grain": "overall",
                    "formula_description": "sum active subscriptions",
                    "business_purpose": "revenue tracking",
                    "interpretation_notes": "higher is better",
                    "risk_if_misread": "overstates cash",
                    "allowed_null_policy": "not allowed",
                    "enabled": True,
                },
                {
                    "metric_name": "custom_metric",
                    "display_name": "Custom Metric",
                    "category": "custom_metric_family",
                    "business_owner": "Operations",
                    "grain": "overall",
                    "formula_description": "custom formula",
                    "business_purpose": "custom tracking",
                    "interpretation_notes": "custom notes",
                    "risk_if_misread": "custom risk",
                    "allowed_null_policy": "allowed",
                    "enabled": True,
                },
            ]
        }
    )

    expected_files = {
        "executive_summary.md",
        "data_quality_report.md",
        "intervention_plan.md",
        "risk_register.md",
        "metric_definitions.md",
    }
    assert {path.name for path in tmp_path.iterdir()} == expected_files
    for filename in expected_files:
        assert (tmp_path / filename).read_text(encoding="utf-8").strip()

    executive = (tmp_path / "executive_summary.md").read_text(encoding="utf-8")
    risk_register = (tmp_path / "risk_register.md").read_text(encoding="utf-8")
    data_quality = (tmp_path / "data_quality_report.md").read_text(encoding="utf-8")
    definitions = (tmp_path / "metric_definitions.md").read_text(encoding="utf-8")

    assert "Generated: 2026-05-01" in executive
    assert "Fix / Billing" in executive
    assert "Customer: C1 next" in executive
    assert "Failed / Payment" in risk_register
    assert "Retry now" in risk_register
    assert "customers/raw" in data_quality
    assert "billing / join risk with newline" in data_quality
    assert "## Revenue Metrics" in definitions
    assert "MRR / Current" in definitions
    assert "### Custom Metric" in definitions
    assert "## Custom Metric Family Metrics" in definitions


def test_report_generator_handles_empty_report_inputs(tmp_path):
    generator = ReportGenerator(
        reports_dir=tmp_path,
        generated_on=date(2026, 5, 1),
    )

    generator.generate_data_quality_report([])
    generator.generate_intervention_plan([])
    generator.generate_risk_register({"risk_profiles": [], "leakages": []})
    generator.generate_metric_definitions({"metrics": []})

    assert "No data quality results available" in (tmp_path / "data_quality_report.md").read_text(
        encoding="utf-8"
    )
    assert "No interventions generated" in (tmp_path / "intervention_plan.md").read_text(
        encoding="utf-8"
    )
    assert "No high/critical risk customers identified" in (
        tmp_path / "risk_register.md"
    ).read_text(encoding="utf-8")
    assert "authoritative metric glossary" in (tmp_path / "metric_definitions.md").read_text(
        encoding="utf-8"
    )


def test_executive_summary_handles_empty_recommendations(tmp_path):
    generator = ReportGenerator(
        reports_dir=tmp_path,
        generated_on=date(2026, 5, 1),
    )

    generator.generate_executive_summary({"kpis": [], "leakages": [], "recommendations": []})

    assert "No recommendations generated." in (tmp_path / "executive_summary.md").read_text(
        encoding="utf-8"
    )


def test_table_separator_helper_renders_markdown_separator():
    assert _table_separator(1, 2, 3) == "| --- | --- | --- |"
