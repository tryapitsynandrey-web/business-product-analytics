import pandas as pd
import pytest
from app.ui_helpers_customer import (
    build_custom_scenario_analysis,
    determine_business_status,
    quality_status_for_score,
    build_data_quality_overview,
    prepare_quality_dimension_summary,
    prepare_quality_issue_queue,
    filter_customer_360,
    build_customer_360_overview,
    prepare_customer_360_queue,
    build_customer_profile_summary,
    summarize_filter_state,
)


def test_build_custom_scenario_analysis_uses_dashboard_inputs():
    kpis = pd.DataFrame(
        [
            {"metric_name": "monthly_recurring_revenue", "value": 100_000.0},
            {"metric_name": "customer_churn_rate", "value": 0.05},
            {"metric_name": "activation_rate", "value": 0.20},
            {"metric_name": "average_revenue_per_user", "value": 50.0},
        ]
    )
    customers = pd.DataFrame(
        [
            {"customer_id": "C1", "current_mrr": 50.0},
            {"customer_id": "C2", "current_mrr": 0.0},
            {"customer_id": "C3", "current_mrr": 100.0},
        ]
    )
    leakages = pd.DataFrame(
        [
            {"leakage_type": "Failed Payment", "estimated_revenue_loss": 1_000.0},
            {"leakage_type": "Refund", "estimated_revenue_loss": 500.0},
        ]
    )

    scenarios = build_custom_scenario_analysis(
        kpis,
        customers,
        leakages,
        churn_improvement_rate=0.20,
        activation_improvement_rate=0.50,
        arpu_increase_rate=0.10,
        failed_payment_recovery_rate=0.25,
    )

    assert scenarios["scenario_name"].tolist() == [
        "Churn Reduction",
        "Activation Increase",
        "ARPU Increase",
        "Failed Payment Recovery",
    ]
    assert scenarios.loc[0, "monthly_impact"] == 1_000.0
    assert scenarios.loc[1, "monthly_impact"] == pytest.approx(15.0)
    assert scenarios.loc[2, "monthly_impact"] == pytest.approx(10.0)
    assert scenarios.loc[3, "monthly_impact"] == 250.0


def test_build_custom_scenario_analysis_returns_schema_without_inputs():
    scenarios = build_custom_scenario_analysis(
        None,
        None,
        None,
        churn_improvement_rate=0.10,
        activation_improvement_rate=0.10,
        arpu_increase_rate=0.05,
        failed_payment_recovery_rate=0.30,
    )

    assert scenarios.empty
    assert scenarios.columns.tolist() == [
        "scenario_name",
        "baseline_value",
        "simulated_value",
        "monthly_impact",
        "annualized_impact",
        "confidence_note",
    ]


def test_determine_business_status_prioritizes_worst_status():
    assert determine_business_status(pd.DataFrame({"status": ["Healthy", "Watch"]})) == "Watch"
    assert determine_business_status(pd.DataFrame({"status": ["Risk", "Healthy"]})) == "Risk"
    assert (
        determine_business_status(pd.DataFrame({"status": ["Critical", "Healthy"]})) == "Critical"
    )
    assert determine_business_status(pd.DataFrame({"status": ["Healthy", "Good"]})) == "Healthy"
    assert determine_business_status(pd.DataFrame()) == "Unknown"


def test_quality_status_for_score_uses_expected_bands():
    assert quality_status_for_score(0.95) == "Good"
    assert quality_status_for_score(0.8) == "Watch"
    assert quality_status_for_score(0.6) == "Risk"
    assert quality_status_for_score(0.4) == "Critical"
    assert quality_status_for_score("bad") == "Unknown"


def test_build_data_quality_overview_summarizes_scores():
    df = pd.DataFrame(
        [
            {
                "dataset": "customers",
                "completeness_score": 0.95,
                "uniqueness_score": 1.0,
                "validity_score": 0.9,
                "referential_integrity_score": 1.0,
                "overall_score": 0.9625,
                "status": "Good",
                "business_risk": "Low",
            },
            {
                "dataset": "subscriptions",
                "completeness_score": 0.7,
                "uniqueness_score": 0.8,
                "validity_score": 0.6,
                "referential_integrity_score": 0.4,
                "overall_score": 0.65,
                "status": "Risk",
                "business_risk": "High",
            },
        ]
    )

    overview = build_data_quality_overview(df)

    assert overview["datasets"] == 2
    assert overview["average_score_display"] == "80.6%"
    assert overview["needs_attention"] == 1
    assert overview["worst_status"] == "Risk"
    assert overview["lowest_dimension"] == "Referential Integrity"


def test_build_data_quality_overview_without_overall_or_status():
    df = pd.DataFrame(
        [
            {"dataset": "customers", "completeness_score": 0.8, "validity_score": 0.7},
            {"dataset": "subscriptions"},
        ]
    )

    overview = build_data_quality_overview(df)

    assert overview["datasets"] == 2
    assert overview["needs_attention"] == 2


def test_build_data_quality_overview_without_score_columns():
    overview = build_data_quality_overview(pd.DataFrame([{"dataset": "customers"}]))

    assert overview["lowest_dimension"] == "Unknown"
    assert overview["lowest_dimension_score"] == 0.0


def test_build_data_quality_overview_handles_empty_status_series_branch():
    class NonEmptyFrame(pd.DataFrame):
        @property
        def _constructor(self):
            return NonEmptyFrame

        @property
        def empty(self):
            return False

    overview = build_data_quality_overview(NonEmptyFrame(columns=["overall_score"]))

    assert overview["datasets"] == 0
    assert overview["worst_status"] == "Unknown"


def test_prepare_quality_dimension_summary_orders_lowest_first():
    df = pd.DataFrame(
        [
            {
                "completeness_score": 0.9,
                "uniqueness_score": 1.0,
                "validity_score": 0.7,
                "referential_integrity_score": 0.8,
            }
        ]
    )

    summary = prepare_quality_dimension_summary(df)

    assert summary["dimension"].tolist()[0] == "Validity"
    assert summary.iloc[0]["status"] == "Risk"


def test_prepare_quality_dimension_summary_skips_missing_and_invalid_columns():
    summary = prepare_quality_dimension_summary(
        pd.DataFrame([{"dataset": "customers", "completeness_score": "bad"}])
    )

    assert summary.empty


def test_prepare_quality_issue_queue_adds_weakest_dimension_and_sorts_risk():
    df = pd.DataFrame(
        [
            {
                "dataset": "customers",
                "completeness_score": 0.95,
                "uniqueness_score": 1.0,
                "validity_score": 0.9,
                "referential_integrity_score": 1.0,
                "overall_score": 0.96,
                "status": "Good",
                "business_risk": "Low",
            },
            {
                "dataset": "subscriptions",
                "completeness_score": 0.5,
                "uniqueness_score": 0.7,
                "validity_score": 0.6,
                "referential_integrity_score": 0.4,
                "overall_score": 0.55,
                "status": "Risk",
                "business_risk": "High",
            },
        ]
    )

    queue = prepare_quality_issue_queue(df)

    assert queue["dataset"].tolist() == ["subscriptions", "customers"]
    assert queue.iloc[0]["lowest_dimension"] == "Referential Integrity"
    assert queue.iloc[0]["lowest_dimension_score"] == 0.4


def test_prepare_quality_issue_queue_derives_missing_columns():
    queue = prepare_quality_issue_queue(
        pd.DataFrame(
            [
                {"dataset": "customers", "completeness_score": "bad"},
                {"dataset": "subscriptions", "validity_score": 0.8},
            ]
        )
    )

    assert queue.iloc[0]["dataset"] == "customers"
    assert queue.iloc[0]["status"] == "Critical"
    assert queue.iloc[0]["business_risk"] == ""


def test_quality_helpers_handle_missing_data():
    assert build_data_quality_overview(None)["datasets"] == 0
    assert prepare_quality_dimension_summary(None).empty
    assert prepare_quality_issue_queue(None).empty
    assert prepare_quality_issue_queue(pd.DataFrame({"status": ["Good"]})).empty


def test_filter_customer_360_handles_empty_and_optional_filters():
    df = pd.DataFrame([{"customer_id": "C1", "segment": "SMB"}])

    assert filter_customer_360(None).empty
    assert filter_customer_360(df)["customer_id"].tolist() == ["C1"]


def test_filter_customer_360_applies_common_filters():
    df = pd.DataFrame(
        [
            {"customer_id": "C1", "churn_risk_band": "High", "segment": "SMB", "plan": "Pro"},
            {
                "customer_id": "C2",
                "churn_risk_band": "Low",
                "segment": "Enterprise",
                "plan": "Basic",
            },
        ]
    )

    filtered = filter_customer_360(df, risk_bands=["High"], segments=["SMB"], plans=["Pro"])

    assert len(filtered) == 1
    assert filtered.iloc[0]["customer_id"] == "C1"


def test_build_customer_360_overview_summarizes_active_view():
    df = pd.DataFrame(
        [
            {
                "customer_id": "C1",
                "is_active": True,
                "churn_risk_band": "High",
                "current_mrr": 100,
                "revenue_at_risk": 100,
                "churn_risk_score": 0.8,
                "main_driver": "Low NPS",
            },
            {
                "customer_id": "C2",
                "is_active": False,
                "churn_risk_band": "Low",
                "current_mrr": 0,
                "revenue_at_risk": 0,
                "churn_risk_score": 0.1,
                "main_driver": "Low NPS",
            },
            {
                "customer_id": "C3",
                "is_active": "active",
                "churn_risk_band": "Critical",
                "current_mrr": 200,
                "revenue_at_risk": 150,
                "churn_risk_score": 0.9,
                "main_driver": "Failed Payments",
            },
        ]
    )

    overview = build_customer_360_overview(df)

    assert overview["customers"] == 3
    assert overview["active_customers"] == 2
    assert overview["high_risk_customers"] == 2
    assert overview["revenue_at_risk"] == 250.0
    assert overview["current_mrr"] == 300.0
    assert overview["average_risk_score"] == pytest.approx(0.6)
    assert overview["top_driver"] == "Low NPS"


def test_build_customer_360_overview_handles_empty_and_missing_columns():
    assert build_customer_360_overview(None)["customers"] == 0

    overview = build_customer_360_overview(
        pd.DataFrame(
            [
                {"customer_id": "C1", "current_mrr": 100, "main_driver": "Unknown"},
                {"customer_id": "C2", "current_mrr": 0, "main_driver": None},
            ]
        )
    )

    assert overview["active_customers"] == 1
    assert overview["high_risk_customers"] == 0
    assert overview["top_driver"] == "Unknown"

    missing_driver = build_customer_360_overview(pd.DataFrame([{"customer_id": "C1"}]))
    assert missing_driver["top_driver"] == "Unknown"


def test_prepare_customer_360_queue_sorts_and_limits_by_risk():
    df = pd.DataFrame(
        [
            {
                "customer_id": "C2",
                "churn_risk_band": "Low",
                "churn_risk_score": 0.1,
                "revenue_at_risk": 10,
                "current_mrr": 50,
            },
            {
                "customer_id": "C3",
                "churn_risk_band": "Critical",
                "churn_risk_score": 0.7,
                "revenue_at_risk": 50,
                "current_mrr": 100,
            },
            {
                "customer_id": "C1",
                "churn_risk_band": "High",
                "churn_risk_score": 0.9,
                "revenue_at_risk": 200,
                "current_mrr": 150,
            },
        ]
    )

    queue = prepare_customer_360_queue(df, limit=2)

    assert queue["customer_id"].tolist() == ["C3", "C1"]
    assert queue.columns.tolist() == [
        "customer_id",
        "churn_risk_band",
        "current_mrr",
        "revenue_at_risk",
        "churn_risk_score",
    ]


def test_prepare_customer_360_queue_handles_empty_and_missing_customer_id():
    assert prepare_customer_360_queue(None).empty

    queue = prepare_customer_360_queue(
        pd.DataFrame([{"churn_risk_band": "High", "revenue_at_risk": 25}])
    )

    assert queue["customer_id"].tolist() == [""]
    assert queue["revenue_at_risk"].tolist() == [25]


def test_build_customer_profile_summary_returns_display_fields():
    row = {
        "customer_id": "C1",
        "segment": "SMB",
        "plan": "Pro",
        "churn_risk_band": "High",
        "current_mrr": 199.0,
        "revenue_at_risk": 199.0,
        "usage_trend": "Declining",
        "recommended_action": "Call customer",
    }

    summary = build_customer_profile_summary(row)

    assert summary["Customer"] == "C1"
    assert summary["Revenue at Risk"] == 199.0
    assert summary["Recommended Action"] == "Call customer"


def test_summarize_filter_state():
    assert summarize_filter_state({"Priority": ["High"], "Owner": []}) == "Priority: High"
    assert summarize_filter_state({"Priority": []}) == "No filters applied"
    assert summarize_filter_state({"Priority": []}, empty_label="All rows") == "All rows"

