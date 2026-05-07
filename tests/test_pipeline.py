"""
Tests for src/core/pipeline.py
"""

from __future__ import annotations

import os
import pytest
from core.pipeline import ProductAnalyticsPipeline

class TestPipelineIntegration:
    def test_pipeline_runs_successfully_end_to_end(self):
        """
        Integration test verifying the pipeline completes fully end-to-end.

        Asserts:
        - pipeline.run() returns success=True
        - validation_passed=True (all generated synthetic datasets are clean)
        - generated_outputs is non-empty
        - no exception is raised
        """
        pipeline = ProductAnalyticsPipeline()
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
            "data/exports/metric_lineage.csv"
        ]
        for expected in expected_artifacts:
            assert expected in outputs_str

    def test_pipeline_sqlite_disabled_by_default(self):
        pipeline = ProductAnalyticsPipeline()
        assert pipeline._sqlite_enabled is False

    def test_pipeline_sqlite_enabled(self, tmp_path):
        db_path = tmp_path / "test.db"
        pipeline = ProductAnalyticsPipeline()
        
        # Override config programmatically
        pipeline._sqlite_enabled = True
        pipeline._sqlite_path = str(db_path)
        
        result = pipeline.run()
        
        assert result.success is True
        assert db_path.exists()
        
        outputs_str = " ".join(result.generated_outputs)
        assert "sqlite://kpi_summary" in outputs_str
        assert "sqlite://data_quality_scores" in outputs_str
