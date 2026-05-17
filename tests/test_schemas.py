from models.schemas import (
    DATASET_NAMES, CUSTOMER_COLUMNS, DATASET_SCHEMAS,
    OUTPUT_SCHEMAS, KPI_SUMMARY_COLUMNS, CUSTOMER_360_COLUMNS,
    DATA_QUALITY_SCORE_COLUMNS, HEALTH_SCORE_COLUMNS,
    INTERVENTION_PLAN_COLUMNS, CHURN_RISK_PROFILE_COLUMNS,
    DECISION_TRACE_COLUMNS, METRIC_LINEAGE_COLUMNS,
    RECOMMENDATION_COLUMNS, REVENUE_LEAKAGE_COLUMNS
)

def test_schema_constants_exist():
    assert "customers" in DATASET_NAMES
    assert "customer_id" in CUSTOMER_COLUMNS
    assert "is_active" in CUSTOMER_COLUMNS

def test_dataset_schemas():
    assert "customers" in DATASET_SCHEMAS
    cust_schema = DATASET_SCHEMAS["customers"]
    assert cust_schema.dataset_name == "customers"
    assert cust_schema.primary_key == "customer_id"
    assert "customer_id" in cust_schema.required_columns

def test_dataset_schemas_match_config_required_columns():
    import yaml
    from utils.paths import CONFIG_DIR

    config = yaml.safe_load((CONFIG_DIR / "config.yaml").read_text())
    for dataset, columns in config["required_columns"].items():
        assert dataset in DATASET_SCHEMAS
        assert DATASET_SCHEMAS[dataset].required_columns == columns

def test_output_schema_constants_exist():
    assert len(KPI_SUMMARY_COLUMNS) > 0
    assert len(CUSTOMER_360_COLUMNS) > 0
    assert len(DATA_QUALITY_SCORE_COLUMNS) > 0
    assert len(HEALTH_SCORE_COLUMNS) > 0
    assert len(INTERVENTION_PLAN_COLUMNS) > 0
    assert len(CHURN_RISK_PROFILE_COLUMNS) > 0
    assert len(DECISION_TRACE_COLUMNS) > 0
    assert len(METRIC_LINEAGE_COLUMNS) > 0
    assert len(RECOMMENDATION_COLUMNS) > 0
    assert len(REVENUE_LEAKAGE_COLUMNS) > 0

def test_output_schemas_mapping_exists():
    expected_keys = [
        "kpi_summary", "customer_360", "data_quality_scores", "health_scores",
        "intervention_plan", "churn_risk_profiles", "decision_traces",
        "metric_lineage", "recommendations", "revenue_leakage", "ui_metric_catalog"
    ]
    for key in expected_keys:
        assert key in OUTPUT_SCHEMAS
        assert len(OUTPUT_SCHEMAS[key]) > 0

def test_output_schemas_no_duplicates():
    for name, schema in OUTPUT_SCHEMAS.items():
        assert len(schema) == len(set(schema)), f"Schema {name} has duplicate columns"

def test_sqlite_schemas():
    from models.schemas import SQLITE_TABLE_SCHEMAS
    assert SQLITE_TABLE_SCHEMAS == OUTPUT_SCHEMAS
    for name, schema in SQLITE_TABLE_SCHEMAS.items():
        assert len(schema) > 0

def test_sqlite_allowed_tables():
    from models.schemas import SQLITE_ALLOWED_TABLES, OUTPUT_SCHEMAS
    assert len(SQLITE_ALLOWED_TABLES) > 0
    assert len(SQLITE_ALLOWED_TABLES) == len(set(SQLITE_ALLOWED_TABLES))
    for table in SQLITE_ALLOWED_TABLES:
        assert table in OUTPUT_SCHEMAS

def test_sqlite_ui_query_tables():
    from models.schemas import SQLITE_UI_QUERY_TABLES, SQLITE_ALLOWED_TABLES
    assert len(SQLITE_UI_QUERY_TABLES) > 0
    assert len(SQLITE_UI_QUERY_TABLES) == len(set(SQLITE_UI_QUERY_TABLES))
    for table in SQLITE_UI_QUERY_TABLES:
        assert table in SQLITE_ALLOWED_TABLES
