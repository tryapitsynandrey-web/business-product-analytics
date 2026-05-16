import pytest
import pandas as pd
from core.metric_lineage import MetricLineageEngine

@pytest.fixture
def metric_catalog():
    return {
        "metrics": [
            {
                "metric_name": "customer_churn_rate",
                "display_name": "Churn Rate",
                "category": "Customer",
                "source_datasets": ["subscriptions"],
                "required_columns_by_dataset": {
                    "subscriptions": ["customer_id", "status"],
                },
                "formula_description": "churned / total",
                "business_owner": "Product",
                "business_purpose": "Measure retention",
                "risk_if_misread": "False confidence"
            }
        ]
    }

def test_build_lineage_table(metric_catalog):
    engine = MetricLineageEngine()
    df = engine.build_lineage_table(metric_catalog)
    assert not df.empty
    assert len(df) == 1
    assert df["metric_name"].iloc[0] == "customer_churn_rate"
    assert df["source_datasets"].iloc[0] == "subscriptions"

def test_valid_source_datasets(metric_catalog):
    engine = MetricLineageEngine()
    lineage = engine.validate_lineage_sources(metric_catalog, ["subscriptions", "customers"])
    assert lineage[0]["lineage_status"] == "Valid"

def test_missing_source_dataset(metric_catalog):
    engine = MetricLineageEngine()
    lineage = engine.validate_lineage_sources(metric_catalog, ["customers"])
    assert "Missing Source" in lineage[0]["lineage_status"]

def test_empty_catalog():
    engine = MetricLineageEngine()
    df = engine.build_lineage_table({})
    assert df.empty
    assert "metric_name" in df.columns

def test_required_columns_flattened(metric_catalog):
    engine = MetricLineageEngine()
    df = engine.build_lineage_table(metric_catalog)
    cols = df["required_columns"].iloc[0]
    assert "subscriptions.customer_id" in cols
    assert "subscriptions.status" in cols

def test_current_catalog_shape_is_supported():
    from core.metric_governance import MetricGovernance

    catalog = MetricGovernance()._catalog
    df = MetricLineageEngine().build_lineage_table(catalog)

    assert not df.empty
    assert "Unknown" not in set(df["metric_name"])
    assert df["source_datasets"].replace("", pd.NA).notna().all()
