"""
Tests for src/core/pipeline.py
"""

from __future__ import annotations

import yaml
import pandas as pd
import pytest

from adapters.sqlite_reader import SQLiteReader
import core.pipeline as pipeline_module
from core.pipeline import (
    ProductAnalyticsPipeline,
    _load_config,
    _parse_config_date,
    _parse_sqlite_if_exists,
)
from utils.validation import ValidationIssue, ValidationResult
from utils.paths import PROJECT_ROOT


def _write_test_config(tmp_path, *, sqlite_enabled: bool = False):
    config = yaml.safe_load((PROJECT_ROOT / "config" / "config.yaml").read_text())
    config["synthetic_data"]["num_customers"] = 80
    config["paths"] = {
        "data_dir": str(tmp_path / "data"),
        "synthetic_data_dir": str(tmp_path / "data" / "synthetic"),
        "processed_data_dir": str(tmp_path / "data" / "processed"),
        "exports_dir": str(tmp_path / "data" / "exports"),
        "reports_dir": str(tmp_path / "reports"),
    }
    config["persistence"]["sqlite"]["enabled"] = sqlite_enabled
    config["persistence"]["sqlite"]["path"] = str(tmp_path / "data" / "local" / "test.db")

    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
    return config_path


def _make_pipeline_for_unit_tests(tmp_path, **overrides):
    tmp_path.mkdir(parents=True, exist_ok=True)
    config_path = _write_test_config(tmp_path)
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    for section, values in overrides.items():
        config.setdefault(section, {}).update(values)
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
    return ProductAnalyticsPipeline(config_path=config_path)


class TestPipelineIntegration:
    def test_pipeline_runs_successfully_end_to_end(self, tmp_path):
        """
        Integration test verifying the pipeline completes fully end-to-end.

        Asserts:
        - pipeline.run() returns success=True
        - validation_passed=True (all generated synthetic datasets are clean)
        - generated_outputs is non-empty
        - no exception is raised
        """
        pipeline = ProductAnalyticsPipeline(config_path=_write_test_config(tmp_path))
        result = pipeline.run()

        assert result is not None
        assert result.success is True
        assert result.validation_passed is True
        assert len(result.generated_outputs) > 0

        outputs_str = " ".join(result.generated_outputs)

        expected_artifacts = [
            "data/processed/kpi_summary.csv",
            "data/processed/customer_360.csv",
            "data/processed/data_quality_scores.csv",
            "data/processed/health_scores.csv",
            "data/processed/intervention_plan.csv",
            "data/exports/churn_risk_profiles.csv",
            "data/exports/revenue_leakage.csv",
            "data/exports/recommendations.csv",
            "data/exports/decision_traces.csv",
            "data/exports/metric_lineage.csv",
        ]
        for expected in expected_artifacts:
            assert expected in outputs_str

        kpis = pd.read_csv(tmp_path / "data" / "processed" / "kpi_summary.csv")
        assert kpis["metric_name"].value_counts()["revenue_at_risk"] == 1

        lineage = pd.read_csv(tmp_path / "data" / "exports" / "metric_lineage.csv")
        assert "Unknown" not in set(lineage["metric_name"])
        assert lineage["source_datasets"].notna().all()

    def test_pipeline_sqlite_disabled_by_default(self, tmp_path):
        pipeline = ProductAnalyticsPipeline(config_path=_write_test_config(tmp_path))
        assert pipeline._sqlite_enabled is False

    def test_pipeline_sqlite_enabled(self, tmp_path):
        db_path = tmp_path / "data" / "local" / "test.db"
        pipeline = ProductAnalyticsPipeline(
            config_path=_write_test_config(tmp_path, sqlite_enabled=True)
        )

        result = pipeline.run()

        assert result.success is True
        assert db_path.exists()

        outputs_str = " ".join(result.generated_outputs)
        assert "sqlite://kpi_summary" in outputs_str
        assert "sqlite://data_quality_scores" in outputs_str

        risk_profiles = SQLiteReader(db_path).read_table("churn_risk_profiles")
        assert not risk_profiles.empty
        assert set(risk_profiles["risk_band"]).issubset({"Low", "Medium", "High", "Critical"})

    def test_pipeline_outputs_are_reproducible(self, tmp_path):
        config_path = _write_test_config(tmp_path)

        first = ProductAnalyticsPipeline(config_path=config_path).run()
        assert first.success is True
        first_kpis = (tmp_path / "data" / "processed" / "kpi_summary.csv").read_text()
        first_traces = (tmp_path / "data" / "exports" / "decision_traces.csv").read_text()
        first_plan = (tmp_path / "data" / "processed" / "intervention_plan.csv").read_text()

        second = ProductAnalyticsPipeline(config_path=config_path).run()
        assert second.success is True
        assert (tmp_path / "data" / "processed" / "kpi_summary.csv").read_text() == first_kpis
        assert (tmp_path / "data" / "exports" / "decision_traces.csv").read_text() == first_traces
        assert (tmp_path / "data" / "processed" / "intervention_plan.csv").read_text() == first_plan


def test_load_config_raises_for_missing_config(tmp_path):
    with pytest.raises(FileNotFoundError, match="Configuration file not found"):
        _load_config(tmp_path / "missing.yaml")


def test_config_parsers_cover_defaults_and_invalid_values():
    assert _parse_config_date(None).isoformat()
    assert _parse_config_date(None, default=pd.Timestamp("2026-05-01").date()).isoformat() == (
        "2026-05-01"
    )
    assert _parse_sqlite_if_exists("replace") == "replace"
    with pytest.raises(ValueError, match="persistence.sqlite.if_exists"):
        _parse_sqlite_if_exists("truncate")


def test_phase_validate_logs_error_result(monkeypatch, tmp_path):
    pipeline = _make_pipeline_for_unit_tests(tmp_path)
    issue = ValidationIssue(
        dataset="customers",
        check_name="required_columns",
        severity="error",
        message="missing customer_id",
        affected_column="customer_id",
        affected_rows_count=1,
    )
    validation = ValidationResult(
        passed=False,
        issues=[issue],
        total_checks=1,
        failed_checks=1,
    )
    monkeypatch.setattr(
        pipeline_module, "run_dataset_validation", lambda datasets, config: validation
    )

    result = pipeline._phase_validate({"customers": pd.DataFrame()})

    assert result.passed is False


def test_phase_write_outputs_handles_empty_optional_artifacts(monkeypatch, tmp_path):
    pipeline = _make_pipeline_for_unit_tests(tmp_path)
    monkeypatch.setattr(pipeline.governance, "get_catalog", lambda: {})
    empty_decision = {
        "customer_360": pd.DataFrame(),
        "data_quality_scores": [],
        "health_scores": pd.DataFrame(),
        "interventions": [],
        "decision_traces": [],
        "metric_lineage": pd.DataFrame(),
    }
    empty_analytics = {
        "kpis": [],
        "risk_profiles": [],
        "leakages": [],
        "recommendations": [],
    }

    written = pipeline._phase_write_outputs(empty_analytics, empty_decision)

    assert written == [
        "reports/executive_summary.md",
        "reports/data_quality_report.md",
        "reports/intervention_plan.md",
        "reports/risk_register.md",
    ]


def test_phase_write_sqlite_outputs_handles_empty_and_write_failure(monkeypatch, tmp_path):
    pipeline = _make_pipeline_for_unit_tests(tmp_path, persistence={"sqlite": {"enabled": True}})

    def empty_write(db_path, artifacts, if_exists):
        assert artifacts == {}
        return []

    monkeypatch.setattr(pipeline.output_serializer, "write_sqlite_artifacts", empty_write)
    assert pipeline._phase_write_sqlite_outputs({"kpis": []}, {}) == []

    def failing_write(db_path, artifacts, if_exists):
        raise RuntimeError("sqlite down")

    monkeypatch.setattr(pipeline.output_serializer, "write_sqlite_artifacts", failing_write)
    assert pipeline._phase_write_sqlite_outputs({"kpis": []}, {}) == []


def test_phase_decision_layer_handles_empty_data_quality_scores(monkeypatch, tmp_path):
    pipeline = _make_pipeline_for_unit_tests(tmp_path)
    monkeypatch.setattr(pipeline.governance, "get_catalog", lambda: {})

    class EmptyDataQualityScorer:
        def __init__(self, issues, datasets, primary_keys):
            self.issues = issues
            self.datasets = datasets
            self.primary_keys = primary_keys

        def generate_quality_summary(self):
            return []

    class EmptyCustomer360Engine:
        def __init__(self, datasets, risk_profiles, recommendations):
            self.datasets = datasets
            self.risk_profiles = risk_profiles
            self.recommendations = recommendations

        def build_customer_360_view(self):
            return pd.DataFrame()

    class PassthroughSegmentationEngine:
        def assign_customer_segments(self, customer_360):
            return customer_360

    monkeypatch.setattr(pipeline_module, "DataQualityScorer", EmptyDataQualityScorer)
    monkeypatch.setattr(pipeline_module, "Customer360Engine", EmptyCustomer360Engine)
    monkeypatch.setattr(pipeline_module, "SegmentationEngine", PassthroughSegmentationEngine)
    monkeypatch.setattr(pipeline.intervention_planner, "create_intervention_plan", lambda recs: [])

    decision = pipeline._phase_decision_layer(
        {},
        {"kpis": [], "risk_profiles": [], "leakages": [], "recommendations": []},
        [],
    )

    assert decision["data_quality_scores"] == []
    assert decision["health_scores"].empty


def test_run_returns_validation_failure_without_analytics(monkeypatch, tmp_path):
    pipeline = _make_pipeline_for_unit_tests(
        tmp_path,
        pipeline={
            "generate_synthetic_data": False,
            "run_validation": True,
            "write_outputs": False,
        },
    )
    issue = ValidationIssue(
        dataset="customers",
        check_name="not_empty",
        severity="error",
        message="customers empty",
        affected_column="",
        affected_rows_count=0,
    )
    validation = ValidationResult(
        passed=False,
        issues=[issue],
        total_checks=1,
        failed_checks=1,
    )
    monkeypatch.setattr(pipeline, "_phase_load", lambda: {"customers": pd.DataFrame()})
    monkeypatch.setattr(pipeline, "_phase_validate", lambda datasets: validation)

    result = pipeline.run()

    assert result.success is False
    assert result.issues == ["customers empty"]


def test_run_success_without_validation_or_output_writes(monkeypatch, tmp_path):
    pipeline = _make_pipeline_for_unit_tests(
        tmp_path,
        pipeline={
            "generate_synthetic_data": False,
            "run_validation": False,
            "write_outputs": False,
        },
    )
    monkeypatch.setattr(pipeline, "_phase_load", lambda: {})
    monkeypatch.setattr(pipeline, "_phase_analytics", lambda datasets: {"kpis": []})
    monkeypatch.setattr(
        pipeline,
        "_phase_decision_layer",
        lambda datasets, analytics, issues: {},
    )

    result = pipeline.run()

    assert result.success is True
    assert result.outputs_written is False
    assert result.generated_outputs == []


def test_run_returns_file_not_found_and_unexpected_errors(monkeypatch, tmp_path):
    pipeline = _make_pipeline_for_unit_tests(
        tmp_path,
        pipeline={"generate_synthetic_data": False},
    )
    monkeypatch.setattr(
        pipeline, "_phase_load", lambda: (_ for _ in ()).throw(FileNotFoundError("missing data"))
    )
    missing = pipeline.run()

    pipeline = _make_pipeline_for_unit_tests(
        tmp_path / "unexpected",
        pipeline={"generate_synthetic_data": False, "run_validation": False},
    )
    monkeypatch.setattr(pipeline, "_phase_load", lambda: {})
    monkeypatch.setattr(
        pipeline, "_phase_analytics", lambda datasets: (_ for _ in ()).throw(RuntimeError("boom"))
    )
    unexpected = pipeline.run()

    assert missing.success is False
    assert missing.message == "missing data"
    assert unexpected.success is False
    assert unexpected.message == "Unexpected error: boom"
