from __future__ import annotations

from dataclasses import asdict
from datetime import date, datetime

from models.customer import CustomerProfile
from models.enums import (
    HealthStatus,
    InterventionType,
    Plan,
    RiskBand,
    Segment,
    SubscriptionStatus,
)
from models.metrics import MetricRegistryEntry, MetricRegistryResult, MetricResult
from models.recommendation import BusinessRecommendation
from models.scenario import ScenarioResult
from models.schemas import DATASET_SCHEMAS, OUTPUT_SCHEMAS, DatasetSchema
from models.subscription import SubscriptionState
from models.transaction import TransactionEvent


def test_enum_values_match_business_labels():
    assert Segment.MID_MARKET.value == "Mid-Market"
    assert Plan.ENTERPRISE.value == "Enterprise"
    assert SubscriptionStatus.PAST_DUE.value == "Past Due"
    assert RiskBand.CRITICAL.value == "Critical"
    assert HealthStatus.WATCH.value == "Watch"
    assert InterventionType.BILLING_RECOVERY.value == "Billing Recovery"


def test_dataset_schema_primary_keys_are_present_in_required_columns():
    assert all(isinstance(schema, DatasetSchema) for schema in DATASET_SCHEMAS.values())
    for schema in DATASET_SCHEMAS.values():
        if schema.primary_key is not None:
            assert schema.primary_key in schema.required_columns


def test_output_schemas_have_required_columns_and_no_duplicates():
    required_artifacts = {
        "kpi_summary",
        "customer_360",
        "data_quality_scores",
        "health_scores",
        "intervention_plan",
        "churn_risk_profiles",
        "decision_traces",
        "metric_lineage",
        "recommendations",
        "revenue_leakage",
    }
    assert required_artifacts.issubset(OUTPUT_SCHEMAS)
    for artifact_name, columns in OUTPUT_SCHEMAS.items():
        assert columns, f"{artifact_name} has an empty output schema"
        assert len(columns) == len(set(columns)), f"{artifact_name} has duplicate columns"


def test_domain_dataclasses_can_be_instantiated_and_serialized():
    customer = CustomerProfile(
        customer_id="C1",
        company_name="Acme",
        segment=Segment.SMB,
        country="USA",
        signup_date=date(2026, 1, 1),
        acquisition_channel="Direct",
        is_active=True,
    )
    subscription = SubscriptionState(
        subscription_id="S1",
        customer_id="C1",
        plan=Plan.PRO,
        status=SubscriptionStatus.ACTIVE,
        start_date=date(2026, 1, 1),
        end_date=None,
        monthly_price=199.0,
        billing_cycle="Monthly",
        auto_renew=True,
    )
    transaction = TransactionEvent(
        transaction_id="T1",
        customer_id="C1",
        subscription_id="S1",
        amount=199.0,
        currency="USD",
        status="Success",
        transaction_date=datetime(2026, 1, 2, 12, 0),
        payment_method="Credit Card",
    )
    scenario = ScenarioResult(
        scenario_name="Reduce churn",
        metric_affected="MRR",
        baseline_value=10_000.0,
        simulated_value=11_000.0,
        monthly_impact=1_000.0,
        annualized_impact=12_000.0,
        confidence_note="Rule-based estimate",
    )

    assert asdict(customer)["segment"] == Segment.SMB
    assert asdict(subscription)["status"] == SubscriptionStatus.ACTIVE
    assert asdict(transaction)["amount"] == 199.0
    assert asdict(scenario)["annualized_impact"] == 12_000.0


def test_metric_registry_dataclasses_capture_counts_and_metadata():
    metric = MetricResult(
        metric_name="monthly_recurring_revenue",
        value=1000.0,
        date_calculated=date(2026, 5, 1),
        grain="overall",
        explanation="Test metric",
    )
    entry = MetricRegistryEntry(
        metric_name=metric.metric_name,
        display_name="MRR",
        category="Revenue",
        source_datasets=["subscriptions"],
        required_columns_by_dataset={"subscriptions": ["monthly_price"]},
        business_owner="Finance",
        business_purpose="Track recurring revenue",
        interpretation_notes="Higher is better",
        risk_if_misread="Can overstate cash",
        enabled=True,
        implementation_key="KPIEngine.calculate_monthly_recurring_revenue",
        implementation_status="Mapped",
    )
    registry = MetricRegistryResult(
        entries=[entry],
        mapped_count=1,
        unmapped_count=0,
        disabled_count=0,
    )

    assert metric.explanation == "Test metric"
    assert registry.entries[0].implementation_status == "Mapped"
    assert registry.mapped_count + registry.unmapped_count + registry.disabled_count == 1


def test_business_recommendation_uses_existing_intervention_type_enum():
    recommendation = BusinessRecommendation(
        recommendation_id="REC-1",
        intervention_type=InterventionType.RETENTION,
        target_segment="Enterprise",
        affected_customers=["C1"],
        expected_revenue_protected=5000.0,
        expected_revenue_created=0.0,
        effort_level="High",
        confidence=0.85,
        priority_score=90.0,
        suggested_owner="Customer Success",
        implementation_rationale="Protect high-risk account",
    )

    assert recommendation.intervention_type == InterventionType.RETENTION
    assert recommendation.affected_customers == ["C1"]
