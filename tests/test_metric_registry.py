import pytest
from core.metric_governance import MetricGovernance, IMPLEMENTATION_MAP


@pytest.fixture
def governance():
    return MetricGovernance()


def test_metric_registry_builds_entries(governance):
    registry = governance.build_metric_registry()
    assert len(registry.entries) > 0
    assert registry.mapped_count + registry.unmapped_count + registry.disabled_count == len(
        registry.entries
    )


def test_registry_entry_has_correct_status(governance):
    mrr_entry = governance.get_registry_entry("monthly_recurring_revenue")
    assert mrr_entry.metric_name == "monthly_recurring_revenue"
    assert mrr_entry.implementation_status in ["Mapped", "Disabled"]


def test_enabled_registry_entries(governance):
    enabled = governance.get_enabled_registry_entries()
    assert len(enabled) > 0
    for e in enabled:
        assert e.enabled is True


def test_mapped_metrics(governance):
    mapped = governance.get_mapped_metrics()
    for e in mapped:
        assert e.implementation_status == "Mapped"
        assert e.implementation_key is not None


def test_unmapped_metrics_returns_list(governance):
    unmapped = governance.get_unmapped_metrics()
    assert isinstance(unmapped, list)


def test_unknown_metric_raises_key_error(governance):
    with pytest.raises(KeyError, match="not defined in the metric catalog"):
        governance.get_registry_entry("non_existent_metric_xyz")


def test_ui_metric_catalog_schema(governance):
    catalog = governance.build_ui_metric_catalog()
    assert len(catalog) > 0
    first = catalog[0]
    expected_keys = {
        "metric_name",
        "display_name",
        "category",
        "business_owner",
        "business_purpose",
        "interpretation_notes",
        "risk_if_misread",
        "enabled",
        "implementation_status",
    }
    assert set(first.keys()) == expected_keys


def test_has_implementation(governance):
    # known mapped metric
    assert governance.metric_has_implementation("monthly_recurring_revenue") is True
    # unknown metric
    assert governance.metric_has_implementation("invalid_fake_metric") is False


def test_business_health_metrics_mapped(governance):
    assert governance.metric_has_implementation("gross_profit") is True
    assert governance.metric_has_implementation("customer_lifetime_value") is True
    assert governance.metric_has_implementation("churn_exposure") is True


def test_unmapped_metrics_remain_safely_unmapped(governance):
    unmapped = governance.get_unmapped_metrics()
    # If there are any unmapped metrics, their implementation_key must be None
    for e in unmapped:
        assert e.implementation_key is None
        assert e.implementation_status == "Unmapped"


def test_no_disabled_metric_is_incorrectly_marked_mapped(governance):
    registry = governance.build_metric_registry()
    for e in registry.entries:
        if not e.enabled:
            assert e.implementation_status == "Disabled"


def test_implementation_map_functions_exist():
    import importlib

    for metric_name, impl_key in IMPLEMENTATION_MAP.items():
        if impl_key.startswith("KPIEngine."):
            from core.kpi_engine import KPIEngine

            method_name = impl_key.split(".")[1]
            assert hasattr(KPIEngine, method_name), f"KPIEngine missing method {method_name}"
        elif impl_key.startswith("business_health."):
            # impl_key is like "business_health.profitability.calculate_gross_profit"
            parts = impl_key.split(".")
            module_path = "core." + ".".join(parts[:-1])
            func_name = parts[-1]
            mod = importlib.import_module(module_path)
            assert hasattr(mod, func_name), f"{module_path} missing function {func_name}"
