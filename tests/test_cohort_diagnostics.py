import pytest
import pandas as pd
from contrib.cohort_diagnostics import CohortDiagnosticsEngine


@pytest.fixture
def cohort_summary():
    return pd.DataFrame(
        [
            {"cohort_month": "2023-01", "period_number": 1, "retention_rate": 0.85},
            {"cohort_month": "2023-02", "period_number": 1, "retention_rate": 0.60},
            {"cohort_month": "2023-03", "period_number": 1, "retention_rate": 0.72},
            {"cohort_month": "2023-04", "period_number": 1, "retention_rate": 0.78},
        ]
    )


def test_delta_calculation(cohort_summary):
    engine = CohortDiagnosticsEngine()
    df = engine.calculate_cohort_delta(cohort_summary, 0.80)
    assert df[df["cohort_month"] == "2023-01"]["delta"].iloc[0] == pytest.approx(0.05, rel=1e-5)
    assert df[df["cohort_month"] == "2023-02"]["delta"].iloc[0] == pytest.approx(-0.20, rel=1e-5)


def test_status_mapping(cohort_summary):
    engine = CohortDiagnosticsEngine()
    df = engine.identify_weak_cohorts(cohort_summary, 0.80)
    assert df[df["cohort_month"] == "2023-01"]["status"].iloc[0] == "Healthy"
    assert df[df["cohort_month"] == "2023-02"]["status"].iloc[0] == "Critical"
    assert (
        df[df["cohort_month"] == "2023-03"]["status"].iloc[0] == "Watch"
    )  # -0.08 is between -0.05 and -0.10
    assert df[df["cohort_month"] == "2023-04"]["status"].iloc[0] == "Healthy"


def test_status_mapping_includes_risk_band():
    engine = CohortDiagnosticsEngine()
    summary = pd.DataFrame(
        [{"cohort_month": "2023-05", "period_number": 1, "retention_rate": 0.69}]
    )

    df = engine.identify_weak_cohorts(summary, 0.80)

    assert df.iloc[0]["status"] == "Risk"


def test_diagnostics_output_structure(cohort_summary):
    engine = CohortDiagnosticsEngine()
    df = engine.build_cohort_diagnostics(cohort_summary, 0.80)
    assert "likely_driver" in df.columns
    assert "recommended_action" in df.columns
    assert len(df) == 4


def test_healthy_cohort_handling(cohort_summary):
    engine = CohortDiagnosticsEngine()
    df = engine.build_cohort_diagnostics(cohort_summary, 0.80)
    healthy = df[df["status"] == "Healthy"].iloc[0]
    assert healthy["likely_driver"] == "N/A"


def test_diagnose_cohort_drivers_assigns_action_for_weak_cohort(cohort_summary):
    engine = CohortDiagnosticsEngine()
    weak = engine.identify_weak_cohorts(cohort_summary, 0.80)

    diagnosed = engine.diagnose_cohort_drivers(weak)

    critical = diagnosed[diagnosed["status"] == "Critical"].iloc[0]
    assert critical["likely_driver"] == "Low Engagement or Support Issues"
    assert critical["recommended_action"] == "Investigate cohort onboarding"


def test_empty_cohort_diagnostics_return_stable_schema():
    engine = CohortDiagnosticsEngine()

    df = engine.build_cohort_diagnostics(pd.DataFrame(), 0.80)

    assert list(df.columns) == [
        "cohort_month",
        "period_number",
        "retention_rate",
        "baseline_retention",
        "delta",
        "status",
        "likely_driver",
        "recommended_action",
    ]


def test_empty_cohort_helpers_return_stable_schemas():
    engine = CohortDiagnosticsEngine()

    assert list(engine.calculate_cohort_delta(pd.DataFrame(), 0.8).columns) == [
        "cohort_month",
        "period_number",
        "retention_rate",
        "baseline_retention",
        "delta",
    ]
    assert "status" in engine.identify_weak_cohorts(pd.DataFrame(), 0.8).columns
    assert "recommended_action" in engine.diagnose_cohort_drivers(pd.DataFrame()).columns
