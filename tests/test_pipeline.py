"""
Tests for src/core/pipeline.py
"""

from __future__ import annotations

import yaml
import pandas as pd

from adapters.sqlite_reader import SQLiteReader
from core.pipeline import ProductAnalyticsPipeline
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
