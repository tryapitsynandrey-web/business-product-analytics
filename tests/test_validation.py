"""
Tests for src/utils/validation.py

All tests use small in-memory pandas DataFrames.
No external services or real customer data are used.
"""

import pandas as pd
import pytest

from utils.validation import (
    ValidationIssue,
    ValidationResult,
    run_dataset_validation,
    validate_allowed_values,
    validate_date_columns,
    validate_no_duplicate_keys,
    validate_not_empty,
    validate_nps_range,
    validate_numeric_non_negative,
    validate_referential_integrity,
    validate_required_columns,
    validate_required_datasets,
)


# ---------------------------------------------------------------------------
# Fixtures — reusable minimal DataFrames
# ---------------------------------------------------------------------------

@pytest.fixture()
def valid_customers() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "customer_id": ["C1", "C2", "C3"],
            "company_name": ["Acme", "Beta", "Gamma"],
            "segment": ["SMB", "Enterprise", "SMB"],
            "country": ["USA", "UK", "USA"],
            "signup_date": ["2023-01-01", "2023-03-15", "2024-07-20"],
            "acquisition_channel": ["Organic Search", "Direct", "Referral"],
            "is_active": [True, True, False],
        }
    )


@pytest.fixture()
def valid_subscriptions() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "subscription_id": ["S1", "S2", "S3"],
            "customer_id": ["C1", "C2", "C3"],
            "plan": ["Basic", "Pro", "Premium"],
            "status": ["Active", "Active", "Canceled"],
            "start_date": ["2023-01-01", "2023-03-15", "2024-07-20"],
            "monthly_price": [49.0, 199.0, 499.0],
            "billing_cycle": ["Monthly", "Monthly", "Monthly"],
        }
    )


@pytest.fixture()
def valid_nps() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "score_id": ["N1", "N2"],
            "customer_id": ["C1", "C2"],
            "date": ["2023-06-01", "2023-09-01"],
            "score": [8, 5],
        }
    )


# ---------------------------------------------------------------------------
# Minimal config for run_dataset_validation
# ---------------------------------------------------------------------------

@pytest.fixture()
def minimal_config() -> dict:
    return {
        "required_datasets": ["customers", "subscriptions"],
        "required_columns": {
            "customers": ["customer_id", "company_name", "segment"],
            "subscriptions": ["subscription_id", "customer_id", "status", "monthly_price"],
        },
        "primary_keys": {
            "customers": "customer_id",
            "subscriptions": "subscription_id",
        },
        "date_columns": {
            "customers": ["signup_date"],
            "subscriptions": ["start_date"],
        },
        "referential_integrity": [
            {
                "child_dataset": "subscriptions",
                "child_key": "customer_id",
                "parent_dataset": "customers",
                "parent_key": "customer_id",
            }
        ],
        "domain_constraints": {
            "allowed_subscription_statuses": ["Active", "Canceled", "Past Due", "Trial", "Expired"],
            "allowed_payment_statuses": ["Success", "Failed", "Refunded"],
            "nps": {"min_score": 0, "max_score": 10},
            "non_negative_columns": {
                "subscriptions": ["monthly_price"],
            },
        },
    }


# ---------------------------------------------------------------------------
# Test: validate_required_datasets
# ---------------------------------------------------------------------------

class TestValidateRequiredDatasets:
    def test_all_present_returns_no_issues(self, valid_customers, valid_subscriptions):
        issues = validate_required_datasets(
            {"customers": valid_customers, "subscriptions": valid_subscriptions},
            ["customers", "subscriptions"],
        )
        assert issues == []

    def test_missing_dataset_returns_one_error(self, valid_customers):
        issues = validate_required_datasets(
            {"customers": valid_customers},
            ["customers", "subscriptions"],
        )
        assert len(issues) == 1
        assert issues[0].dataset == "subscriptions"
        assert issues[0].severity == "error"

    def test_all_missing_returns_one_error_per_dataset(self):
        issues = validate_required_datasets({}, ["customers", "subscriptions", "transactions"])
        assert len(issues) == 3


# ---------------------------------------------------------------------------
# Test: validate_required_columns
# ---------------------------------------------------------------------------

class TestValidateRequiredColumns:
    def test_all_columns_present_returns_no_issues(self, valid_customers):
        issues = validate_required_columns(
            valid_customers, ["customer_id", "segment", "country"], "customers"
        )
        assert issues == []

    def test_missing_column_returns_error(self, valid_customers):
        issues = validate_required_columns(
            valid_customers, ["customer_id", "nonexistent_col"], "customers"
        )
        assert len(issues) == 1
        assert issues[0].affected_column == "nonexistent_col"

    def test_multiple_missing_columns_each_produce_an_issue(self, valid_customers):
        issues = validate_required_columns(
            valid_customers, ["missing_a", "missing_b"], "customers"
        )
        assert len(issues) == 2


# ---------------------------------------------------------------------------
# Test: validate_no_duplicate_keys
# ---------------------------------------------------------------------------

class TestValidateNoDuplicateKeys:
    def test_unique_keys_returns_no_issues(self, valid_customers):
        issues = validate_no_duplicate_keys(valid_customers, "customer_id", "customers")
        assert issues == []

    def test_duplicate_key_returns_error(self):
        df = pd.DataFrame({"customer_id": ["C1", "C1", "C2"]})
        issues = validate_no_duplicate_keys(df, "customer_id", "customers")
        assert len(issues) == 1
        assert issues[0].affected_rows_count == 1  # 1 duplicate value

    def test_missing_key_column_returns_no_issues(self, valid_customers):
        # Column existence is a separate check; this must not crash.
        issues = validate_no_duplicate_keys(valid_customers, "nonexistent_id", "customers")
        assert issues == []


# ---------------------------------------------------------------------------
# Test: validate_not_empty
# ---------------------------------------------------------------------------

class TestValidateNotEmpty:
    def test_non_empty_df_passes(self, valid_customers):
        issues = validate_not_empty(valid_customers, "customers")
        assert issues == []

    def test_empty_df_returns_error(self):
        issues = validate_not_empty(pd.DataFrame(), "customers")
        assert len(issues) == 1
        assert issues[0].severity == "error"


# ---------------------------------------------------------------------------
# Test: validate_date_columns
# ---------------------------------------------------------------------------

class TestValidateDateColumns:
    def test_valid_dates_return_no_issues(self, valid_customers):
        issues = validate_date_columns(valid_customers, ["signup_date"], "customers")
        assert issues == []

    def test_invalid_date_string_returns_error(self):
        df = pd.DataFrame(
            {"signup_date": ["2023-01-01", "not-a-date", "2024-12-31"]}
        )
        issues = validate_date_columns(df, ["signup_date"], "customers")
        assert len(issues) == 1
        assert issues[0].affected_rows_count == 1

    def test_missing_column_skipped_gracefully(self, valid_customers):
        # Should not raise; missing columns are caught by a different check.
        issues = validate_date_columns(valid_customers, ["nonexistent_date"], "customers")
        assert issues == []


# ---------------------------------------------------------------------------
# Test: validate_allowed_values
# ---------------------------------------------------------------------------

class TestValidateAllowedValues:
    def test_all_values_allowed_returns_no_issues(self, valid_subscriptions):
        issues = validate_allowed_values(
            valid_subscriptions,
            "status",
            ["Active", "Canceled", "Past Due"],
            "subscriptions",
        )
        assert issues == []

    def test_disallowed_value_returns_error(self):
        df = pd.DataFrame({"status": ["Active", "Unknown", "Canceled"]})
        issues = validate_allowed_values(df, "status", ["Active", "Canceled"], "subscriptions")
        assert len(issues) == 1
        assert issues[0].affected_rows_count == 1

    def test_missing_column_returns_no_issues(self, valid_subscriptions):
        issues = validate_allowed_values(
            valid_subscriptions, "nonexistent", ["A"], "subscriptions"
        )
        assert issues == []


# ---------------------------------------------------------------------------
# Test: validate_numeric_non_negative
# ---------------------------------------------------------------------------

class TestValidateNumericNonNegative:
    def test_positive_values_return_no_issues(self, valid_subscriptions):
        issues = validate_numeric_non_negative(
            valid_subscriptions, ["monthly_price"], "subscriptions"
        )
        assert issues == []

    def test_negative_value_returns_error(self):
        df = pd.DataFrame({"amount": [100.0, -50.0, 200.0]})
        issues = validate_numeric_non_negative(df, ["amount"], "transactions")
        assert len(issues) == 1
        assert issues[0].affected_rows_count == 1

    def test_zero_is_acceptable(self):
        df = pd.DataFrame({"amount": [0.0, 100.0]})
        issues = validate_numeric_non_negative(df, ["amount"], "transactions")
        assert issues == []


# ---------------------------------------------------------------------------
# Test: validate_nps_range
# ---------------------------------------------------------------------------

class TestValidateNpsRange:
    def test_valid_scores_return_no_issues(self, valid_nps):
        issues = validate_nps_range(valid_nps, "score", 0, 10)
        assert issues == []

    def test_score_above_max_returns_error(self):
        df = pd.DataFrame({"score_id": ["N1"], "customer_id": ["C1"], "date": ["2023-01-01"], "score": [11]})
        issues = validate_nps_range(df, "score", 0, 10)
        assert len(issues) == 1
        assert issues[0].check_name == "nps_range"

    def test_score_below_min_returns_error(self):
        df = pd.DataFrame({"score_id": ["N1"], "customer_id": ["C1"], "date": ["2023-01-01"], "score": [-1]})
        issues = validate_nps_range(df, "score", 0, 10)
        assert len(issues) == 1

    def test_missing_column_returns_no_issues(self, valid_nps):
        issues = validate_nps_range(valid_nps, "nonexistent", 0, 10)
        assert issues == []

    def test_custom_dataset_name_is_used(self, valid_nps):
        df = pd.DataFrame({"score_id": ["N1"], "customer_id": ["C1"], "date": ["2023-01-01"], "score": [11]})
        issues = validate_nps_range(df, "score", 0, 10, dataset_name="custom_nps")
        assert len(issues) == 1
        assert issues[0].dataset == "custom_nps"


# ---------------------------------------------------------------------------
# Test: validate_referential_integrity
# ---------------------------------------------------------------------------

class TestValidateReferentialIntegrity:
    def test_all_child_keys_exist_in_parent(self, valid_customers, valid_subscriptions):
        issues = validate_referential_integrity(
            valid_customers, valid_subscriptions,
            "customer_id", "customer_id",
            "customers", "subscriptions",
        )
        assert issues == []

    def test_orphaned_child_key_returns_error(self, valid_customers):
        orphan_subs = pd.DataFrame(
            {
                "subscription_id": ["S99"],
                "customer_id": ["C_DOES_NOT_EXIST"],
                "status": ["Active"],
            }
        )
        issues = validate_referential_integrity(
            valid_customers, orphan_subs,
            "customer_id", "customer_id",
            "customers", "subscriptions",
        )
        assert len(issues) == 1
        assert issues[0].affected_rows_count == 1

    def test_missing_column_returns_no_issues(self, valid_customers, valid_subscriptions):
        issues = validate_referential_integrity(
            valid_customers, valid_subscriptions,
            "nonexistent", "customer_id",
            "customers", "subscriptions",
        )
        assert issues == []


# ---------------------------------------------------------------------------
# Test: run_dataset_validation (integration)
# ---------------------------------------------------------------------------

class TestRunDatasetValidation:
    def test_clean_datasets_pass_validation(
        self, valid_customers, valid_subscriptions, minimal_config
    ):
        datasets = {"customers": valid_customers, "subscriptions": valid_subscriptions}
        result = run_dataset_validation(datasets, minimal_config)
        assert result.passed is True
        assert result.failed_checks == 0

    def test_missing_required_dataset_fails_validation(
        self, valid_customers, minimal_config
    ):
        # subscriptions is required but absent
        result = run_dataset_validation({"customers": valid_customers}, minimal_config)
        assert result.passed is False
        assert any(i.dataset == "subscriptions" for i in result.issues)

    def test_duplicate_primary_key_fails_validation(
        self, valid_subscriptions, minimal_config
    ):
        dup_customers = pd.DataFrame(
            {
                "customer_id": ["C1", "C1"],  # intentional duplicate
                "company_name": ["Acme", "Acme"],
                "segment": ["SMB", "SMB"],
                "signup_date": ["2023-01-01", "2023-01-01"],
            }
        )
        datasets = {"customers": dup_customers, "subscriptions": valid_subscriptions}
        result = run_dataset_validation(datasets, minimal_config)
        assert result.passed is False
        assert any(i.check_name == "no_duplicate_keys" for i in result.issues)

    def test_referential_integrity_failure_fails_validation(
        self, valid_customers, minimal_config
    ):
        orphan_subs = pd.DataFrame(
            {
                "subscription_id": ["S99"],
                "customer_id": ["UNKNOWN"],
                "status": ["Active"],
                "monthly_price": [49.0],
                "start_date": ["2023-01-01"],
            }
        )
        datasets = {"customers": valid_customers, "subscriptions": orphan_subs}
        result = run_dataset_validation(datasets, minimal_config)
        assert result.passed is False
        assert any(i.check_name == "referential_integrity" for i in result.issues)

    def test_total_checks_count_is_non_zero(
        self, valid_customers, valid_subscriptions, minimal_config
    ):
        datasets = {"customers": valid_customers, "subscriptions": valid_subscriptions}
        result = run_dataset_validation(datasets, minimal_config)
        assert result.total_checks > 0
