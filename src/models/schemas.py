from dataclasses import dataclass
from typing import List, Optional

DATASET_NAMES = [
    "customers",
    "subscriptions",
    "transactions",
    "product_usage",
    "support_tickets",
    "nps_scores",
    "acquisition_channels",
    "targets",
]

CUSTOMER_COLUMNS = [
    "customer_id",
    "company_name",
    "segment",
    "country",
    "signup_date",
    "acquisition_channel",
    "is_active",
]
SUBSCRIPTION_COLUMNS = [
    "subscription_id",
    "customer_id",
    "plan",
    "status",
    "start_date",
    "monthly_price",
    "billing_cycle",
]
TRANSACTION_COLUMNS = [
    "transaction_id",
    "customer_id",
    "subscription_id",
    "amount",
    "currency",
    "status",
    "transaction_date",
]
PRODUCT_USAGE_COLUMNS = ["usage_id", "customer_id", "date", "logins", "key_actions"]
SUPPORT_TICKET_COLUMNS = ["ticket_id", "customer_id", "date_opened", "status"]
NPS_COLUMNS = ["score_id", "customer_id", "date", "score"]
ACQUISITION_CHANNEL_COLUMNS = ["channel_name", "cost_per_acquisition"]
TARGET_COLUMNS = ["metric_name", "target_value", "date"]


@dataclass
class DatasetSchema:
    dataset_name: str
    required_columns: List[str]
    primary_key: Optional[str] = None


DATASET_SCHEMAS = {
    "customers": DatasetSchema("customers", CUSTOMER_COLUMNS, "customer_id"),
    "subscriptions": DatasetSchema("subscriptions", SUBSCRIPTION_COLUMNS, "subscription_id"),
    "transactions": DatasetSchema("transactions", TRANSACTION_COLUMNS, "transaction_id"),
    "product_usage": DatasetSchema("product_usage", PRODUCT_USAGE_COLUMNS, None),
    "support_tickets": DatasetSchema("support_tickets", SUPPORT_TICKET_COLUMNS, "ticket_id"),
    "nps_scores": DatasetSchema("nps_scores", NPS_COLUMNS, None),
    "acquisition_channels": DatasetSchema(
        "acquisition_channels", ACQUISITION_CHANNEL_COLUMNS, "channel_name"
    ),
    "targets": DatasetSchema("targets", TARGET_COLUMNS, None),
}

KPI_SUMMARY_COLUMNS = ["metric_name", "value", "grain", "explanation"]
CUSTOMER_360_COLUMNS = [
    "customer_id",
    "segment",
    "is_active",
    "signup_date",
    "country",
    "acquisition_channel",
    "plan",
    "subscription_status",
    "current_mrr",
    "total_revenue",
    "latest_usage_frequency",
    "usage_trend",
    "latest_nps",
    "support_ticket_count",
    "failed_payment_count",
    "churn_risk_score",
    "churn_risk_band",
    "revenue_at_risk",
    "main_driver",
    "recommended_action",
    "health_status",
    "revenue_segment",
    "usage_segment",
    "risk_segment",
    "nps_segment",
]
DATA_QUALITY_SCORE_COLUMNS = [
    "dataset",
    "completeness_score",
    "uniqueness_score",
    "validity_score",
    "referential_integrity_score",
    "overall_score",
    "status",
    "business_risk",
]
HEALTH_SCORE_COLUMNS = ["area", "score", "status", "explanation"]
INTERVENTION_PLAN_COLUMNS = [
    "intervention_id",
    "recommendation_title",
    "category",
    "target_segment",
    "affected_customers",
    "estimated_revenue_impact",
    "expected_action",
    "suggested_owner",
    "confidence_level",
    "effort_level",
    "priority_score",
    "priority_band",
]
CHURN_RISK_PROFILE_COLUMNS = [
    "customer_id",
    "risk_score",
    "risk_band",
    "drivers",
    "revenue_at_risk",
    "explanation",
]
DECISION_TRACE_COLUMNS = [
    "trace_id",
    "created_at",
    "entity_type",
    "entity_id",
    "signal",
    "triggered_rule",
    "evidence",
    "business_impact",
    "generated_action",
    "confidence_level",
]
METRIC_LINEAGE_COLUMNS = [
    "metric_name",
    "display_name",
    "category",
    "source_datasets",
    "required_columns",
    "formula_description",
    "business_owner",
    "business_purpose",
    "risk_if_misread",
    "lineage_status",
]
RECOMMENDATION_COLUMNS = [
    "rule_id",
    "recommendation_title",
    "category",
    "customer_id",
    "segment",
    "reason",
    "affected_customers",
    "estimated_revenue_impact",
    "impact_score",
    "confidence_level",
    "confidence_weight",
    "suggested_owner",
    "evidence_source",
    "priority_score",
    "priority_band",
]
REVENUE_LEAKAGE_COLUMNS = [
    "leakage_type",
    "customer_id",
    "estimated_revenue_loss",
    "estimated_loss",
    "affected_customers",
    "recommended_action",
    "evidence",
]
UI_METRIC_CATALOG_COLUMNS = [
    "metric_name",
    "display_name",
    "category",
    "business_owner",
    "business_purpose",
    "interpretation_notes",
    "risk_if_misread",
    "enabled",
    "implementation_status",
]

OUTPUT_SCHEMAS = {
    "kpi_summary": KPI_SUMMARY_COLUMNS,
    "customer_360": CUSTOMER_360_COLUMNS,
    "data_quality_scores": DATA_QUALITY_SCORE_COLUMNS,
    "health_scores": HEALTH_SCORE_COLUMNS,
    "intervention_plan": INTERVENTION_PLAN_COLUMNS,
    "churn_risk_profiles": CHURN_RISK_PROFILE_COLUMNS,
    "decision_traces": DECISION_TRACE_COLUMNS,
    "metric_lineage": METRIC_LINEAGE_COLUMNS,
    "recommendations": RECOMMENDATION_COLUMNS,
    "revenue_leakage": REVENUE_LEAKAGE_COLUMNS,
    "ui_metric_catalog": UI_METRIC_CATALOG_COLUMNS,
}

# SQLite mappings reuse the same schemas as CSV artifacts
SQLITE_TABLE_SCHEMAS = OUTPUT_SCHEMAS

SQLITE_ALLOWED_TABLES = list(SQLITE_TABLE_SCHEMAS.keys())

SQLITE_UI_QUERY_TABLES = [
    "kpi_summary",
    "health_scores",
    "customer_360",
    "recommendations",
    "intervention_plan",
    "decision_traces",
    "metric_lineage",
]
