"""
MetricGovernance — gatekeeper for metric contract validation.

Responsibility:
    Load metric_catalog.yaml, verify metric existence, validate required
    datasets and columns, and expose metric definitions for downstream engines.

This module does NOT calculate metrics. It is a pure gatekeeper.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import yaml

from utils.paths import CONFIG_DIR
from models.metrics import MetricRegistryEntry, MetricRegistryResult

logger = logging.getLogger(__name__)

IMPLEMENTATION_MAP: Dict[str, str] = {
    "monthly_recurring_revenue": "KPIEngine.calculate_mrr",
    "average_revenue_per_user": "KPIEngine.calculate_arpu",
    "expansion_revenue": "KPIEngine.calculate_expansion_revenue",
    "contraction_revenue": "KPIEngine.calculate_contraction_revenue",
    "gross_revenue_retention": "KPIEngine.calculate_gross_revenue_retention",
    "net_revenue_retention": "KPIEngine.calculate_net_revenue_retention",
    "revenue_at_risk": "KPIEngine.calculate_revenue_at_risk",
    "activation_rate": "KPIEngine.calculate_activation_rate",
    "usage_frequency": "KPIEngine.calculate_usage_frequency",
    "key_action_rate": "KPIEngine.calculate_key_action_rate",
    "engagement_drop_rate": "KPIEngine.calculate_engagement_drop_rate",
    "feature_adoption_proxy": "KPIEngine.calculate_feature_adoption_proxy",
    "customer_churn_rate": "KPIEngine.calculate_customer_churn_rate",
    "retention_rate": "KPIEngine.calculate_retention_rate",
    "average_nps": "KPIEngine.calculate_average_nps",
    "support_burden": "KPIEngine.calculate_support_burden",
    "time_to_activation": "KPIEngine.calculate_time_to_activation",
    
    # Business Health Metrics
    "gross_profit": "business_health.profitability.calculate_gross_profit",
    "gross_margin": "business_health.profitability.calculate_gross_margin",
    "operating_margin": "business_health.profitability.calculate_operating_margin",
    "net_margin": "business_health.profitability.calculate_net_margin",
    "ebitda": "business_health.profitability.calculate_ebitda",
    "roi": "business_health.profitability.calculate_roi",
    "annual_recurring_revenue": "business_health.revenue_metrics.calculate_arr",
    "revenue_growth_rate": "business_health.revenue_metrics.calculate_revenue_growth_rate",
    "revenue_concentration": "business_health.revenue_metrics.calculate_revenue_concentration",
    "customer_lifetime_value": "business_health.unit_economics.calculate_ltv",
    "customer_acquisition_cost": "business_health.unit_economics.calculate_cac",
    "ltv_to_cac_ratio": "business_health.unit_economics.calculate_ltv_to_cac_ratio",
    "free_cash_flow": "business_health.cashflow.calculate_free_cash_flow",
    "runway_months": "business_health.cashflow.calculate_runway",
    "customer_growth_rate": "business_health.growth_metrics.calculate_customer_growth_rate",
    "growth_efficiency": "business_health.growth_metrics.calculate_growth_efficiency",
    "revenue_per_employee": "business_health.efficiency_metrics.calculate_revenue_per_employee",
    "sales_efficiency": "business_health.efficiency_metrics.calculate_sales_efficiency",
    "customer_concentration_risk": "business_health.risk_metrics.calculate_customer_concentration_risk",
    "churn_exposure": "business_health.risk_metrics.calculate_churn_exposure",
}

# ---------------------------------------------------------------------------
# Structured governance output
# ---------------------------------------------------------------------------

@dataclass
class GovernanceIssue:
    """A single metric governance contract violation."""
    metric_name: str
    check_name: str
    severity: str          # 'error' | 'warning'
    message: str


@dataclass
class GovernanceCheckResult:
    """Outcome of validating a single metric contract."""
    metric_name: str
    passed: bool
    issues: List[GovernanceIssue] = field(default_factory=list)


# ---------------------------------------------------------------------------
# MetricGovernance class
# ---------------------------------------------------------------------------

class MetricGovernance:
    """
    Loads the metric catalog and validates metric contracts against live datasets.

    Parameters
    ----------
    catalog_path : optional
        Override the default config/metric_catalog.yaml location.
    """

    def __init__(self, catalog_path: Optional[Any] = None) -> None:
        self._catalog_path = catalog_path or (CONFIG_DIR / "metric_catalog.yaml")
        self._catalog: Dict[str, Any] = self._load_catalog()
        # Index by metric_name for O(1) lookup
        self._index: Dict[str, Dict[str, Any]] = {
            m["metric_name"]: m
            for m in self._catalog.get("metrics", [])
        }

    # ------------------------------------------------------------------
    # Catalog loading
    # ------------------------------------------------------------------

    def _load_catalog(self) -> Dict[str, Any]:
        with open(self._catalog_path, "r", encoding="utf-8") as fh:
            return yaml.safe_load(fh)

    # ------------------------------------------------------------------
    # Public query methods
    # ------------------------------------------------------------------

    def get_metric_definition(self, metric_name: str) -> Dict[str, Any]:
        """
        Return the full metric definition dict for a given metric_name.

        Raises
        ------
        KeyError
            If the metric is not found in the catalog.
        """
        if metric_name not in self._index:
            raise KeyError(
                f"Metric '{metric_name}' is not defined in the metric catalog. "
                "Verify the metric_name matches config/metric_catalog.yaml."
            )
        return self._index[metric_name]

    def get_enabled_metric_names(self) -> List[str]:
        """Return the names of all enabled metrics in catalog order."""
        return [
            m["metric_name"]
            for m in self._catalog.get("metrics", [])
            if m.get("enabled", True)
        ]

    def metric_exists(self, metric_name: str) -> bool:
        """Return True if the metric_name is present in the catalog."""
        return metric_name in self._index

    # ------------------------------------------------------------------
    # Contract validation
    # ------------------------------------------------------------------

    def validate_metric_contract(
        self,
        metric_name: str,
        datasets: Dict[str, Any],
    ) -> GovernanceCheckResult:
        """
        Validate that a named metric can be legally computed.

        Checks:
          1. Metric exists in catalog.
          2. Metric is enabled.
          3. All source_datasets are present in `datasets`.
          4. All required_columns_by_dataset exist in each respective DataFrame.

        Returns
        -------
        GovernanceCheckResult
            Structured result — does NOT raise on failure so callers can
            decide whether to skip or abort.
        """
        issues: List[GovernanceIssue] = []

        # Check 1: existence
        if metric_name not in self._index:
            issues.append(GovernanceIssue(
                metric_name=metric_name,
                check_name="metric_existence",
                severity="error",
                message=(
                    f"Metric '{metric_name}' is not defined in metric_catalog.yaml."
                ),
            ))
            return GovernanceCheckResult(metric_name=metric_name, passed=False, issues=issues)

        defn = self._index[metric_name]

        # Check 2: enabled flag
        if not defn.get("enabled", True):
            issues.append(GovernanceIssue(
                metric_name=metric_name,
                check_name="metric_enabled",
                severity="warning",
                message=f"Metric '{metric_name}' is disabled in the catalog.",
            ))
            return GovernanceCheckResult(metric_name=metric_name, passed=False, issues=issues)

        # Check 3: required source datasets present
        for ds_name in defn.get("source_datasets", []):
            if ds_name not in datasets:
                issues.append(GovernanceIssue(
                    metric_name=metric_name,
                    check_name="source_dataset_present",
                    severity="error",
                    message=(
                        f"Metric '{metric_name}' requires dataset '{ds_name}', "
                        "which is not present in the loaded datasets."
                    ),
                ))

        # Check 4: required columns per dataset
        col_requirements: Dict[str, List[str]] = defn.get(
            "required_columns_by_dataset", {}
        )
        for ds_name, required_cols in col_requirements.items():
            if ds_name not in datasets:
                continue  # already flagged by check 3
            df = datasets[ds_name]
            for col in required_cols:
                if col not in df.columns:
                    issues.append(GovernanceIssue(
                        metric_name=metric_name,
                        check_name="required_column_present",
                        severity="error",
                        message=(
                            f"Metric '{metric_name}' requires column '{col}' "
                            f"in dataset '{ds_name}', which is missing."
                        ),
                    ))

        passed = not any(i.severity == "error" for i in issues)
        if issues:
            for issue in issues:
                level = logging.WARNING if issue.severity == "warning" else logging.ERROR
                logger.log(level, "[Governance] %s — %s", metric_name, issue.message)

        return GovernanceCheckResult(
            metric_name=metric_name, passed=passed, issues=issues
        )

    def validate_metric(self, metric_name: str, datasets: Dict[str, Any]) -> bool:
        """
        Convenience wrapper used by KPIEngine.

        Returns True if the contract passes, False otherwise.
        Does not raise.
        """
        result = self.validate_metric_contract(metric_name, datasets)
        return result.passed

    # ------------------------------------------------------------------
    # Metric Registry Methods
    # ------------------------------------------------------------------

    def get_registry_entry(self, metric_name: str) -> MetricRegistryEntry:
        defn = self.get_metric_definition(metric_name)
        enabled = defn.get("enabled", True)
        impl_key = IMPLEMENTATION_MAP.get(metric_name)
        
        if not enabled:
            status = "Disabled"
        elif impl_key is not None:
            status = "Mapped"
        else:
            status = "Unmapped"

        return MetricRegistryEntry(
            metric_name=defn["metric_name"],
            display_name=defn.get("display_name", metric_name),
            category=defn.get("category", "Unknown"),
            source_datasets=defn.get("source_datasets", []),
            required_columns_by_dataset=defn.get("required_columns_by_dataset", {}),
            business_owner=defn.get("business_owner", "Unassigned"),
            business_purpose=defn.get("business_purpose", ""),
            interpretation_notes=defn.get("interpretation_notes", ""),
            risk_if_misread=defn.get("risk_if_misread", ""),
            enabled=enabled,
            implementation_key=impl_key,
            implementation_status=status
        )

    def build_metric_registry(self) -> MetricRegistryResult:
        entries = []
        mapped = 0
        unmapped = 0
        disabled = 0
        
        for metric_name in self._index:
            entry = self.get_registry_entry(metric_name)
            entries.append(entry)
            
            if entry.implementation_status == "Mapped":
                mapped += 1
            elif entry.implementation_status == "Disabled":
                disabled += 1
            else:
                unmapped += 1
                
        return MetricRegistryResult(
            entries=entries,
            mapped_count=mapped,
            unmapped_count=unmapped,
            disabled_count=disabled
        )

    def get_enabled_registry_entries(self) -> List[MetricRegistryEntry]:
        registry = self.build_metric_registry()
        return [e for e in registry.entries if e.enabled]

    def get_unmapped_metrics(self) -> List[MetricRegistryEntry]:
        registry = self.build_metric_registry()
        return [e for e in registry.entries if e.implementation_status == "Unmapped"]

    def get_mapped_metrics(self) -> List[MetricRegistryEntry]:
        registry = self.build_metric_registry()
        return [e for e in registry.entries if e.implementation_status == "Mapped"]

    def metric_has_implementation(self, metric_name: str) -> bool:
        if metric_name not in self._index:
            return False
        entry = self.get_registry_entry(metric_name)
        return entry.implementation_status == "Mapped"

    def build_ui_metric_catalog(self) -> List[Dict[str, Any]]:
        """
        Produce a list of dictionaries tailored for UI display.
        Maps directly to UI_METRIC_CATALOG_COLUMNS.
        """
        registry = self.build_metric_registry()
        ui_records = []
        for entry in registry.entries:
            ui_records.append({
                "metric_name": entry.metric_name,
                "display_name": entry.display_name,
                "category": entry.category,
                "business_owner": entry.business_owner,
                "business_purpose": entry.business_purpose,
                "interpretation_notes": entry.interpretation_notes,
                "risk_if_misread": entry.risk_if_misread,
                "enabled": entry.enabled,
                "implementation_status": entry.implementation_status
            })
        return ui_records
