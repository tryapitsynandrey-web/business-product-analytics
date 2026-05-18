from __future__ import annotations

from types import SimpleNamespace

import pandas as pd

from adapters.data_writer import DataWriter
from adapters.output_serializer import OutputSerializer
from models.schemas import (
    CUSTOMER_360_COLUMNS,
    COHORT_SUMMARY_COLUMNS,
    DECISION_TRACE_COLUMNS,
    FUNNEL_SUMMARY_COLUMNS,
    HEALTH_SCORE_COLUMNS,
    INTERVENTION_PLAN_COLUMNS,
    METRIC_LINEAGE_COLUMNS,
    RECOMMENDATION_COLUMNS,
    REVENUE_LEAKAGE_COLUMNS,
    SCENARIO_ANALYSIS_COLUMNS,
    SEGMENT_FUNNEL_COLUMNS,
)


def _row(columns: list[str]) -> dict[str, str]:
    return {column: f"{column}_value" for column in columns}


def _serializer_inputs() -> tuple[SimpleNamespace, SimpleNamespace]:
    analytics = SimpleNamespace(
        kpis=[
            SimpleNamespace(
                metric_name="monthly_recurring_revenue",
                value=100.0,
                grain="monthly",
                explanation="Active subscription MRR",
            )
        ],
        risk_profiles=[
            SimpleNamespace(
                customer_id="C001",
                risk_score=0.85,
                risk_band=SimpleNamespace(value="High"),
                drivers=["low usage", "failed payment"],
                revenue_at_risk=1200.0,
                explanation="Churn risk signals",
            )
        ],
        leakages=[_row(REVENUE_LEAKAGE_COLUMNS)],
        recommendations=[_row(RECOMMENDATION_COLUMNS)],
    )
    decision = SimpleNamespace(
        customer_360=pd.DataFrame([_row(CUSTOMER_360_COLUMNS)]),
        data_quality_scores=[
            SimpleNamespace(
                dataset="customers",
                completeness_score=1.0,
                uniqueness_score=1.0,
                validity_score=1.0,
                referential_integrity_score=1.0,
                overall_score=1.0,
                status="Healthy",
                business_risk="Low",
            )
        ],
        health_scores=pd.DataFrame([_row(HEALTH_SCORE_COLUMNS)]),
        interventions=[_row(INTERVENTION_PLAN_COLUMNS)],
        decision_traces=[_row(DECISION_TRACE_COLUMNS)],
        metric_lineage=pd.DataFrame([_row(METRIC_LINEAGE_COLUMNS)]),
        scenario_analysis=pd.DataFrame([_row(SCENARIO_ANALYSIS_COLUMNS)]),
        cohort_summary=pd.DataFrame([_row(COHORT_SUMMARY_COLUMNS)]),
        funnel_summary=pd.DataFrame([_row(FUNNEL_SUMMARY_COLUMNS)]),
        segment_funnel=pd.DataFrame([_row(SEGMENT_FUNNEL_COLUMNS)]),
    )
    return analytics, decision


def test_build_artifacts_serializes_all_pipeline_outputs():
    serializer = OutputSerializer()
    analytics, decision = _serializer_inputs()

    artifacts = serializer.build_artifacts(analytics, decision)

    assert set(artifacts) == {
        "kpi_summary",
        "customer_360",
        "data_quality_scores",
        "health_scores",
        "intervention_plan",
        "scenario_analysis",
        "cohort_summary",
        "funnel_summary",
        "segment_funnel",
        "churn_risk_profiles",
        "revenue_leakage",
        "recommendations",
        "decision_traces",
        "metric_lineage",
    }
    assert artifacts["churn_risk_profiles"].loc[0, "drivers"] == "low usage | failed payment"


def test_build_artifacts_accepts_mapping_inputs():
    serializer = OutputSerializer()

    artifacts = serializer.build_artifacts({"kpis": []}, {})

    assert artifacts == {}


def test_write_csv_artifacts_persists_processed_and_export_files(tmp_path):
    serializer = OutputSerializer()
    analytics, decision = _serializer_inputs()
    artifacts = serializer.build_artifacts(analytics, decision)
    writer = DataWriter(
        processed_dir=tmp_path / "processed",
        exports_dir=tmp_path / "exports",
        reports_dir=tmp_path / "reports",
    )

    written = serializer.write_csv_artifacts(writer, artifacts)

    assert "data/processed/kpi_summary.csv" in written
    assert "data/exports/recommendations.csv" in written
    assert (tmp_path / "processed" / "kpi_summary.csv").exists()
    assert (tmp_path / "exports" / "metric_lineage.csv").exists()


def test_write_sqlite_artifacts_returns_table_uris(tmp_path):
    serializer = OutputSerializer()
    analytics, decision = _serializer_inputs()
    artifacts = serializer.build_artifacts(analytics, decision)

    written = serializer.write_sqlite_artifacts(
        tmp_path / "productpulse.db",
        {"kpi_summary": artifacts["kpi_summary"]},
        "replace",
    )

    assert written == ["sqlite://kpi_summary"]


def test_build_artifacts_adds_deterministic_run_stamp():
    serializer = OutputSerializer(
        run_id="productpulse-2026-05-01",
        generated_at="2026-05-01T00:00:00+00:00",
    )
    analytics, decision = _serializer_inputs()

    artifacts = serializer.build_artifacts(analytics, decision)

    assert artifacts["kpi_summary"].loc[0, "run_id"] == "productpulse-2026-05-01"
    assert artifacts["kpi_summary"].loc[0, "generated_at"] == "2026-05-01T00:00:00+00:00"

    run_only = OutputSerializer(run_id="run-only").build_artifacts(analytics, decision)
    assert run_only["kpi_summary"].loc[0, "run_id"] == "run-only"
    assert "generated_at" not in run_only["kpi_summary"].columns

    generated_only = OutputSerializer(generated_at="generated-only").build_artifacts(
        analytics,
        decision,
    )
    assert "run_id" not in generated_only["kpi_summary"].columns
    assert generated_only["kpi_summary"].loc[0, "generated_at"] == "generated-only"
