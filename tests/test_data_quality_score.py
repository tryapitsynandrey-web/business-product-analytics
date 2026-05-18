"""
Tests for src/core/data_quality_score.py
"""

from __future__ import annotations

import pytest
import pandas as pd

from core.data_quality_score import DataQualityScorer, DatasetQualityScore
from utils.validation import ValidationIssue


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _clean_datasets() -> dict:
    return {
        "customers": pd.DataFrame({
            "customer_id": ["C1", "C2", "C3"],
            "is_active": [True, True, False],
            "signup_date": ["2023-01-01", "2023-02-01", "2023-03-01"],
        }),
        "subscriptions": pd.DataFrame({
            "subscription_id": ["S1", "S2", "S3"],
            "customer_id": ["C1", "C2", "C3"],
            "status": ["Active", "Active", "Canceled"],
            "monthly_price": [100.0, 200.0, 150.0],
        }),
    }


def _make_issue(dataset: str, check_name: str, severity: str = "error") -> ValidationIssue:
    return ValidationIssue(
        dataset=dataset,
        check_name=check_name,
        severity=severity,
        message=f"Test issue: {check_name}",
        affected_column="test_col",
        affected_rows_count=1,
    )


# ---------------------------------------------------------------------------
# Completeness score
# ---------------------------------------------------------------------------

class TestCompletenessScore:
    def test_fully_populated_dataset_scores_1(self):
        datasets = _clean_datasets()
        scorer = DataQualityScorer([], datasets)
        score = scorer.calculate_completeness_score("customers")
        assert score == pytest.approx(1.0)

    def test_dataset_with_nulls_scores_below_1(self):
        df = pd.DataFrame({
            "id": ["A", "B", "C"],
            "value": [1.0, None, 3.0],
        })
        scorer = DataQualityScorer([], {"test": df})
        score = scorer.calculate_completeness_score("test")
        assert score < 1.0
        assert score > 0.0

    def test_missing_dataset_returns_1(self):
        scorer = DataQualityScorer([], {})
        score = scorer.calculate_completeness_score("nonexistent")
        assert score == pytest.approx(1.0)

    def test_empty_dataset_returns_1(self):
        scorer = DataQualityScorer([], {"empty": pd.DataFrame()})
        score = scorer.calculate_completeness_score("empty")
        assert score == pytest.approx(1.0)

    def test_zero_cell_non_empty_frame_returns_1(self):
        class NonEmptyZeroCellFrame(pd.DataFrame):
            @property
            def empty(self):
                return False

            @property
            def size(self):
                return 0

        scorer = DataQualityScorer([], {"weird": NonEmptyZeroCellFrame()})

        assert scorer.calculate_completeness_score("weird") == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Uniqueness score
# ---------------------------------------------------------------------------

class TestUniquenessScore:
    def test_unique_pk_scores_1(self):
        datasets = _clean_datasets()
        scorer = DataQualityScorer([], datasets, primary_keys={"customers": "customer_id"})
        score = scorer.calculate_uniqueness_score("customers")
        assert score == pytest.approx(1.0)

    def test_duplicate_pk_scores_below_1(self):
        df = pd.DataFrame({
            "id": ["A", "A", "B"],
            "value": [1, 2, 3],
        })
        scorer = DataQualityScorer([], {"test": df}, primary_keys={"test": "id"})
        score = scorer.calculate_uniqueness_score("test")
        assert score < 1.0

    def test_validation_issue_triggers_zero_without_pk(self):
        issue = _make_issue("customers", "no_duplicate_keys")
        scorer = DataQualityScorer([issue], _clean_datasets())
        score = scorer.calculate_uniqueness_score("customers")
        assert score == pytest.approx(0.0)

    def test_empty_dataset_returns_1(self):
        scorer = DataQualityScorer([], {"empty": pd.DataFrame()})

        assert scorer.calculate_uniqueness_score("empty") == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Validity score
# ---------------------------------------------------------------------------

class TestValidityScore:
    def test_no_validity_issues_scores_1(self):
        datasets = _clean_datasets()
        scorer = DataQualityScorer([], datasets)
        score = scorer.calculate_validity_score("customers")
        assert score == pytest.approx(1.0)

    def test_validity_issue_reduces_score(self):
        issue = _make_issue("customers", "allowed_values")
        scorer = DataQualityScorer([issue], _clean_datasets())
        score = scorer.calculate_validity_score("customers")
        assert score < 1.0

    def test_warning_issue_does_not_reduce_validity(self):
        issue = _make_issue("customers", "allowed_values", severity="warning")
        scorer = DataQualityScorer([issue], _clean_datasets())
        score = scorer.calculate_validity_score("customers")
        assert score == pytest.approx(1.0)

    @pytest.mark.parametrize("check_name", ["date_columns", "nps_range"])
    def test_validation_check_names_reduce_validity(self, check_name):
        issue = _make_issue("customers", check_name)
        scorer = DataQualityScorer([issue], _clean_datasets())
        assert scorer.calculate_validity_score("customers") < 1.0


# ---------------------------------------------------------------------------
# Referential integrity score
# ---------------------------------------------------------------------------

class TestReferentialIntegrityScore:
    def test_no_ri_issues_scores_1(self):
        datasets = _clean_datasets()
        scorer = DataQualityScorer([], datasets)
        score = scorer.calculate_referential_integrity_score("subscriptions")
        assert score == pytest.approx(1.0)

    def test_ri_issue_reduces_score(self):
        issue = _make_issue("subscriptions", "referential_integrity")
        scorer = DataQualityScorer([issue], _clean_datasets())
        score = scorer.calculate_referential_integrity_score("subscriptions")
        assert score < 1.0


# ---------------------------------------------------------------------------
# Dataset quality score + status
# ---------------------------------------------------------------------------

class TestDatasetQualityScore:
    def test_clean_data_returns_good_status(self):
        datasets = _clean_datasets()
        scorer = DataQualityScorer([], datasets, primary_keys={"customers": "customer_id"})
        result = scorer.calculate_dataset_quality_score("customers")
        assert isinstance(result, DatasetQualityScore)
        assert result.status == "Good"
        assert result.overall_score >= 0.90

    def test_multiple_errors_can_produce_risk_status(self):
        issues = [
            _make_issue("customers", "allowed_values"),
            _make_issue("customers", "allowed_values"),
            _make_issue("customers", "allowed_values"),
            _make_issue("customers", "referential_integrity"),
            _make_issue("customers", "referential_integrity"),
        ]
        # Force a low uniqueness by using duplicate IDs
        df = pd.DataFrame({"customer_id": ["A", "A", "A"], "val": [1, 2, 3]})
        scorer = DataQualityScorer(issues, {"customers": df}, primary_keys={"customers": "customer_id"})
        result = scorer.calculate_dataset_quality_score("customers")
        assert result.status in ("Risk", "Critical", "Watch")

    def test_status_mapping_good(self):
        datasets = _clean_datasets()
        scorer = DataQualityScorer([], datasets, primary_keys={
            "customers": "customer_id",
            "subscriptions": "subscription_id",
        })
        result = scorer.calculate_dataset_quality_score("subscriptions")
        assert result.status in ("Good", "Watch")

    def test_business_risk_is_non_empty_string(self):
        datasets = _clean_datasets()
        scorer = DataQualityScorer([], datasets)
        result = scorer.calculate_dataset_quality_score("customers")
        assert isinstance(result.business_risk, str)
        assert len(result.business_risk) > 0

    def test_watch_and_critical_status_bands(self):
        class FixedScoreScorer(DataQualityScorer):
            def __init__(self, score: float):
                super().__init__([], {"customers": pd.DataFrame({"id": [1]})})
                self.score = score

            def calculate_completeness_score(self, dataset_name: str) -> float:
                return self.score

            def calculate_uniqueness_score(self, dataset_name: str) -> float:
                return self.score

            def calculate_validity_score(self, dataset_name: str) -> float:
                return self.score

            def calculate_referential_integrity_score(self, dataset_name: str) -> float:
                return self.score

        assert FixedScoreScorer(0.8).calculate_dataset_quality_score("customers").status == "Watch"
        assert (
            FixedScoreScorer(0.2).calculate_dataset_quality_score("customers").status
            == "Critical"
        )


# ---------------------------------------------------------------------------
# Quality summary
# ---------------------------------------------------------------------------

class TestQualitySummary:
    def test_summary_produces_one_record_per_dataset(self):
        datasets = _clean_datasets()
        scorer = DataQualityScorer([], datasets)
        summary = scorer.generate_quality_summary()
        assert len(summary) == len(datasets)

    def test_summary_records_are_typed(self):
        datasets = _clean_datasets()
        scorer = DataQualityScorer([], datasets)
        for record in scorer.generate_quality_summary():
            assert isinstance(record, DatasetQualityScore)
