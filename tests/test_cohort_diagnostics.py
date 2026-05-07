import pytest
import pandas as pd
from core.cohort_diagnostics import CohortDiagnosticsEngine

@pytest.fixture
def cohort_summary():
    return pd.DataFrame([
        {"cohort_month": "2023-01", "period_number": 1, "retention_rate": 0.85},
        {"cohort_month": "2023-02", "period_number": 1, "retention_rate": 0.60},
        {"cohort_month": "2023-03", "period_number": 1, "retention_rate": 0.72},
        {"cohort_month": "2023-04", "period_number": 1, "retention_rate": 0.78}
    ])

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
    assert df[df["cohort_month"] == "2023-03"]["status"].iloc[0] == "Watch" # -0.08 is between -0.05 and -0.10
    assert df[df["cohort_month"] == "2023-04"]["status"].iloc[0] == "Healthy"

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
