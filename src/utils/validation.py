"""
Validation module for ProductPulse analytics pipeline.

All validation functions are pure, deterministic, and side-effect-free.
They return structured ValidationResult objects; they never call sys.exit
or print directly.
"""

from __future__ import annotations

import pandas as pd
from dataclasses import dataclass, field
from typing import Dict, List, Any


# ---------------------------------------------------------------------------
# Structured result types
# ---------------------------------------------------------------------------


@dataclass
class ValidationIssue:
    """Represents a single failed validation check."""

    dataset: str
    check_name: str
    severity: str  # 'error' | 'warning'
    message: str
    affected_column: str
    affected_rows_count: int


@dataclass
class ValidationResult:
    """Aggregated outcome of all validation checks."""

    passed: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    total_checks: int = 0
    failed_checks: int = 0

    def add_issue(self, issue: ValidationIssue) -> None:
        self.issues.append(issue)
        self.failed_checks += 1
        if issue.severity == "error":
            self.passed = False

    def increment_check(self) -> None:
        self.total_checks += 1


# ---------------------------------------------------------------------------
# Individual validation functions
# ---------------------------------------------------------------------------


def validate_required_datasets(
    datasets: Dict[str, pd.DataFrame],
    required_dataset_names: List[str],
) -> List[ValidationIssue]:
    """
    Verify that every expected dataset name is present in the dictionary.

    Returns a list of ValidationIssue objects (one per missing dataset).
    """
    issues: List[ValidationIssue] = []
    for name in required_dataset_names:
        if name not in datasets:
            issues.append(
                ValidationIssue(
                    dataset=name,
                    check_name="required_datasets",
                    severity="error",
                    message=f"Required dataset '{name}' is missing from the loaded datasets.",
                    affected_column="",
                    affected_rows_count=0,
                )
            )
    return issues


def validate_required_columns(
    df: pd.DataFrame,
    required_columns: List[str],
    dataset_name: str,
) -> List[ValidationIssue]:
    """
    Verify that every expected column exists in the DataFrame.
    """
    issues: List[ValidationIssue] = []
    for col in required_columns:
        if col not in df.columns:
            issues.append(
                ValidationIssue(
                    dataset=dataset_name,
                    check_name="required_columns",
                    severity="error",
                    message=(f"Required column '{col}' is missing from dataset '{dataset_name}'."),
                    affected_column=col,
                    affected_rows_count=0,
                )
            )
    return issues


def validate_no_duplicate_keys(
    df: pd.DataFrame,
    key_column: str,
    dataset_name: str,
) -> List[ValidationIssue]:
    """
    Detect duplicate values in the primary-key column.
    """
    issues: List[ValidationIssue] = []
    if key_column not in df.columns:
        return issues  # column-existence is a separate check

    duplicate_count = int(df[key_column].duplicated().sum())
    if duplicate_count > 0:
        issues.append(
            ValidationIssue(
                dataset=dataset_name,
                check_name="no_duplicate_keys",
                severity="error",
                message=(
                    f"Column '{key_column}' in '{dataset_name}' contains "
                    f"{duplicate_count} duplicate value(s)."
                ),
                affected_column=key_column,
                affected_rows_count=duplicate_count,
            )
        )
    return issues


def validate_not_empty(
    df: pd.DataFrame,
    dataset_name: str,
) -> List[ValidationIssue]:
    """
    Fail if the DataFrame has zero rows.
    """
    issues: List[ValidationIssue] = []
    if len(df) == 0:
        issues.append(
            ValidationIssue(
                dataset=dataset_name,
                check_name="not_empty",
                severity="error",
                message=f"Dataset '{dataset_name}' contains zero rows.",
                affected_column="",
                affected_rows_count=0,
            )
        )
    return issues


def validate_date_columns(
    df: pd.DataFrame,
    date_columns: List[str],
    dataset_name: str,
) -> List[ValidationIssue]:
    """
    Attempt to parse each listed column as a date, flagging any that produce
    NaT values beyond those already present in the raw column.
    """
    issues: List[ValidationIssue] = []
    for col in date_columns:
        if col not in df.columns:
            continue  # missing-column check handled elsewhere

        original_null_count = int(df[col].isna().sum())
        try:
            parsed = pd.to_datetime(df[col], errors="coerce")
        except Exception as exc:
            issues.append(
                ValidationIssue(
                    dataset=dataset_name,
                    check_name="date_columns",
                    severity="error",
                    message=f"Column '{col}' in '{dataset_name}' could not be parsed: {exc}",
                    affected_column=col,
                    affected_rows_count=len(df),
                )
            )
            continue

        new_nulls = int(parsed.isna().sum()) - original_null_count
        if new_nulls > 0:
            issues.append(
                ValidationIssue(
                    dataset=dataset_name,
                    check_name="date_columns",
                    severity="error",
                    message=(
                        f"Column '{col}' in '{dataset_name}' contains "
                        f"{new_nulls} unparseable date value(s)."
                    ),
                    affected_column=col,
                    affected_rows_count=new_nulls,
                )
            )
    return issues


def validate_allowed_values(
    df: pd.DataFrame,
    column: str,
    allowed_values: List[Any],
    dataset_name: str,
) -> List[ValidationIssue]:
    """
    Flag rows whose value in `column` is not in `allowed_values`.
    """
    issues: List[ValidationIssue] = []
    if column not in df.columns:
        return issues

    invalid_mask = ~df[column].isin(allowed_values)
    invalid_count = int(invalid_mask.sum())
    if invalid_count > 0:
        issues.append(
            ValidationIssue(
                dataset=dataset_name,
                check_name="allowed_values",
                severity="error",
                message=(
                    f"Column '{column}' in '{dataset_name}' has {invalid_count} "
                    f"row(s) with values not in allowed set: {allowed_values}."
                ),
                affected_column=column,
                affected_rows_count=invalid_count,
            )
        )
    return issues


def validate_numeric_non_negative(
    df: pd.DataFrame,
    columns: List[str],
    dataset_name: str,
) -> List[ValidationIssue]:
    """
    Flag rows where any of the listed numeric columns contain negative values.
    """
    issues: List[ValidationIssue] = []
    for col in columns:
        if col not in df.columns:
            continue

        numeric_series = pd.to_numeric(df[col], errors="coerce")
        negative_count = int((numeric_series < 0).sum())
        if negative_count > 0:
            issues.append(
                ValidationIssue(
                    dataset=dataset_name,
                    check_name="numeric_non_negative",
                    severity="error",
                    message=(
                        f"Column '{col}' in '{dataset_name}' contains "
                        f"{negative_count} negative value(s)."
                    ),
                    affected_column=col,
                    affected_rows_count=negative_count,
                )
            )
    return issues


def validate_nps_range(
    df: pd.DataFrame,
    column: str,
    min_score: int,
    max_score: int,
    dataset_name: str = "nps_scores",
) -> List[ValidationIssue]:
    """
    Verify that all NPS scores fall within [min_score, max_score].
    """
    issues: List[ValidationIssue] = []

    if column not in df.columns:
        return issues

    numeric_scores = pd.to_numeric(df[column], errors="coerce")
    out_of_range = int(((numeric_scores < min_score) | (numeric_scores > max_score)).sum())
    if out_of_range > 0:
        issues.append(
            ValidationIssue(
                dataset=dataset_name,
                check_name="nps_range",
                severity="error",
                message=(
                    f"Column '{column}' contains {out_of_range} score(s) outside "
                    f"the valid range [{min_score}, {max_score}]."
                ),
                affected_column=column,
                affected_rows_count=out_of_range,
            )
        )
    return issues


def validate_referential_integrity(
    parent_df: pd.DataFrame,
    child_df: pd.DataFrame,
    parent_key: str,
    child_key: str,
    parent_name: str,
    child_name: str,
) -> List[ValidationIssue]:
    """
    Verify that every value in child_df[child_key] exists in parent_df[parent_key].
    """
    issues: List[ValidationIssue] = []

    if parent_key not in parent_df.columns or child_key not in child_df.columns:
        return issues

    parent_ids = set(parent_df[parent_key].dropna().unique())
    orphaned_mask = ~child_df[child_key].isin(parent_ids)
    orphan_count = int(orphaned_mask.sum())

    if orphan_count > 0:
        issues.append(
            ValidationIssue(
                dataset=child_name,
                check_name="referential_integrity",
                severity="error",
                message=(
                    f"'{child_name}.{child_key}' has {orphan_count} row(s) that "
                    f"reference non-existent '{parent_name}.{parent_key}' values."
                ),
                affected_column=child_key,
                affected_rows_count=orphan_count,
            )
        )
    return issues


# ---------------------------------------------------------------------------
# Orchestrating function: runs all configured checks in one call
# ---------------------------------------------------------------------------


def run_dataset_validation(
    datasets: Dict[str, pd.DataFrame],
    config: Dict[str, Any],
) -> ValidationResult:
    """
    Execute the full validation suite driven by values from config.yaml.

    Parameters
    ----------
    datasets : dict of dataset_name -> DataFrame (already loaded)
    config   : the parsed config.yaml as a Python dict

    Returns
    -------
    ValidationResult with passed flag, issue list, and check counts.
    """
    result = ValidationResult(passed=True)

    required_datasets: List[str] = config.get("required_datasets", [])
    required_columns_map: Dict[str, List[str]] = config.get("required_columns", {})
    primary_keys_map: Dict[str, str] = config.get("primary_keys", {})
    date_columns_map: Dict[str, List[str]] = config.get("date_columns", {})
    referential_rules: List[Dict[str, str]] = config.get("referential_integrity", [])
    domain = config.get("domain_constraints", {})

    allowed_subscription_statuses: List[str] = domain.get("allowed_subscription_statuses", [])
    allowed_payment_statuses: List[str] = domain.get("allowed_payment_statuses", [])
    nps_cfg: Dict[str, int] = domain.get("nps", {"min_score": 0, "max_score": 10})
    non_negative_cfg: Dict[str, List[str]] = domain.get("non_negative_columns", {})

    # 1. Required datasets present
    result.increment_check()
    for issue in validate_required_datasets(datasets, required_datasets):
        result.add_issue(issue)

    # Per-dataset checks (only for datasets that actually loaded)
    for name, df in datasets.items():
        # 2. Not empty
        result.increment_check()
        for issue in validate_not_empty(df, name):
            result.add_issue(issue)

        # 3. Required columns
        if name in required_columns_map:
            result.increment_check()
            for issue in validate_required_columns(df, required_columns_map[name], name):
                result.add_issue(issue)

        # 4. Duplicate primary keys
        if name in primary_keys_map:
            result.increment_check()
            for issue in validate_no_duplicate_keys(df, primary_keys_map[name], name):
                result.add_issue(issue)

        # 5. Date column parseability
        if name in date_columns_map:
            result.increment_check()
            for issue in validate_date_columns(df, date_columns_map[name], name):
                result.add_issue(issue)

        # 6. Allowed subscription statuses
        if name == "subscriptions" and allowed_subscription_statuses:
            result.increment_check()
            for issue in validate_allowed_values(df, "status", allowed_subscription_statuses, name):
                result.add_issue(issue)

        # 7. Allowed payment statuses
        if name == "transactions" and allowed_payment_statuses:
            result.increment_check()
            for issue in validate_allowed_values(df, "status", allowed_payment_statuses, name):
                result.add_issue(issue)

        # 8. Non-negative numeric columns
        if name in non_negative_cfg:
            result.increment_check()
            for issue in validate_numeric_non_negative(df, non_negative_cfg[name], name):
                result.add_issue(issue)

    # 9. NPS score range
    if "nps_scores" in datasets:
        result.increment_check()
        for issue in validate_nps_range(
            datasets["nps_scores"],
            "score",
            nps_cfg.get("min_score", 0),
            nps_cfg.get("max_score", 10),
        ):
            result.add_issue(issue)

    # 10. Referential integrity
    for rule in referential_rules:
        parent_name = rule["parent_dataset"]
        child_name = rule["child_dataset"]
        if parent_name in datasets and child_name in datasets:
            result.increment_check()
            for issue in validate_referential_integrity(
                parent_df=datasets[parent_name],
                child_df=datasets[child_name],
                parent_key=rule["parent_key"],
                child_key=rule["child_key"],
                parent_name=parent_name,
                child_name=child_name,
            ):
                result.add_issue(issue)

    return result
