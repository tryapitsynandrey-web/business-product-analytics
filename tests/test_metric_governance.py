"""
Tests for src/core/metric_governance.py

Uses the real metric_catalog.yaml via MetricGovernance.
All datasets are in-memory DataFrames.
"""

from __future__ import annotations

import pytest
import pandas as pd
import yaml

from core.metric_governance import MetricGovernance, GovernanceCheckResult


@pytest.fixture()
def governance() -> MetricGovernance:
    return MetricGovernance()


@pytest.fixture()
def minimal_datasets() -> dict:
    return {
        "subscriptions": pd.DataFrame(
            {
                "subscription_id": ["S1"],
                "customer_id": ["C1"],
                "status": ["Active"],
                "monthly_price": [100.0],
                "plan": ["Basic"],
            }
        ),
        "customers": pd.DataFrame(
            {
                "customer_id": ["C1"],
                "is_active": [True],
                "signup_date": ["2023-01-01"],
            }
        ),
        "product_usage": pd.DataFrame(
            {
                "usage_id": ["U1"],
                "customer_id": ["C1"],
                "date": ["2023-06-01"],
                "logins": [20],
                "key_actions": [10],
                "features_used": [3],
            }
        ),
        "nps_scores": pd.DataFrame(
            {
                "score_id": ["N1"],
                "customer_id": ["C1"],
                "date": ["2023-06-01"],
                "score": [8],
            }
        ),
        "support_tickets": pd.DataFrame(
            {
                "ticket_id": ["T1"],
                "customer_id": ["C1"],
            }
        ),
        "transactions": pd.DataFrame(
            {
                "transaction_id": ["TX1"],
                "customer_id": ["C1"],
                "subscription_id": ["S1"],
                "amount": [100.0],
                "status": ["Success"],
            }
        ),
    }


class TestMetricExistence:
    def test_known_metric_exists(self, governance):
        assert governance.metric_exists("monthly_recurring_revenue") is True

    def test_unknown_metric_does_not_exist(self, governance):
        assert governance.metric_exists("made_up_metric_xyz") is False

    def test_get_catalog_returns_top_level_copy(self, governance):
        catalog = governance.get_catalog()
        catalog["metrics"] = []

        assert governance.get_catalog()["metrics"] != []

    def test_get_metric_definition_returns_dict(self, governance):
        defn = governance.get_metric_definition("monthly_recurring_revenue")
        assert isinstance(defn, dict)
        assert defn["metric_name"] == "monthly_recurring_revenue"

    def test_get_metric_definition_raises_for_missing(self, governance):
        with pytest.raises(KeyError):
            governance.get_metric_definition("nonexistent_metric")


class TestEnabledMetrics:
    def test_enabled_metrics_list_is_non_empty(self, governance):
        names = governance.get_enabled_metric_names()
        assert len(names) > 0

    def test_enabled_metrics_includes_mrr(self, governance):
        names = governance.get_enabled_metric_names()
        assert "monthly_recurring_revenue" in names

    def test_all_enabled_metrics_are_strings(self, governance):
        for name in governance.get_enabled_metric_names():
            assert isinstance(name, str)


class TestContractValidation:
    def test_valid_metric_contract_passes(self, governance, minimal_datasets):
        result = governance.validate_metric_contract("monthly_recurring_revenue", minimal_datasets)
        assert isinstance(result, GovernanceCheckResult)
        assert result.passed is True
        assert result.issues == []

    def test_missing_metric_returns_error_issue(self, governance, minimal_datasets):
        result = governance.validate_metric_contract("nonexistent_metric_xyz", minimal_datasets)
        assert result.passed is False
        assert any(i.check_name == "metric_existence" for i in result.issues)

    def test_missing_source_dataset_returns_error(self, governance):
        # Provide no datasets at all
        result = governance.validate_metric_contract("monthly_recurring_revenue", {})
        assert result.passed is False
        assert any(i.check_name == "source_dataset_present" for i in result.issues)

    def test_missing_required_column_returns_error(self, governance):
        # subscriptions present but missing 'monthly_price'
        bad_subs = pd.DataFrame(
            {
                "subscription_id": ["S1"],
                "customer_id": ["C1"],
                "status": ["Active"],
                # monthly_price intentionally omitted
            }
        )
        result = governance.validate_metric_contract(
            "monthly_recurring_revenue", {"subscriptions": bad_subs}
        )
        assert result.passed is False
        assert any(i.check_name == "required_column_present" for i in result.issues)

    def test_validate_metric_convenience_wrapper_returns_bool(self, governance, minimal_datasets):
        passed = governance.validate_metric("monthly_recurring_revenue", minimal_datasets)
        assert passed is True

    def test_validate_metric_returns_false_for_unknown(self, governance, minimal_datasets):
        passed = governance.validate_metric("unknown_metric", minimal_datasets)
        assert passed is False

    def test_disabled_metric_fails_with_warning_issue(self, tmp_path):
        catalog_path = tmp_path / "metric_catalog.yaml"
        catalog_path.write_text(
            yaml.safe_dump(
                {
                    "metrics": [
                        {
                            "metric_name": "disabled_metric",
                            "enabled": False,
                            "source_datasets": [],
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        governance = MetricGovernance(catalog_path=catalog_path)

        result = governance.validate_metric_contract("disabled_metric", {})

        assert result.passed is False
        assert result.issues[0].check_name == "metric_enabled"


class TestMetricRegistry:
    def test_registry_counts_mapped_disabled_and_unmapped_metrics(self, tmp_path):
        catalog_path = tmp_path / "metric_catalog.yaml"
        catalog_path.write_text(
            yaml.safe_dump(
                {
                    "metrics": [
                        {"metric_name": "monthly_recurring_revenue", "enabled": True},
                        {"metric_name": "disabled_metric", "enabled": False},
                        {"metric_name": "unmapped_metric", "enabled": True},
                    ]
                }
            ),
            encoding="utf-8",
        )
        governance = MetricGovernance(catalog_path=catalog_path)

        registry = governance.build_metric_registry()

        assert registry.mapped_count == 1
        assert registry.disabled_count == 1
        assert registry.unmapped_count == 1
        statuses = {entry.metric_name: entry.implementation_status for entry in registry.entries}
        assert statuses["disabled_metric"] == "Disabled"
        assert statuses["unmapped_metric"] == "Unmapped"
