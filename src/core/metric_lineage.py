import pandas as pd
from typing import Dict, Any, List


class MetricLineageEngine:
    def build_metric_lineage(self, metric_catalog: Dict[str, Any]) -> List[Dict[str, Any]]:
        lineage = []
        if not metric_catalog:
            return lineage

        metrics = metric_catalog.get("metrics", [])
        for metric in metrics:
            source_datasets = list(metric.get("source_datasets", []))
            required_columns = []

            required_by_dataset = metric.get("required_columns_by_dataset", {})
            for dataset, columns in required_by_dataset.items():
                if dataset not in source_datasets:
                    source_datasets.append(dataset)
                for col in columns:
                    required_columns.append(f"{dataset}.{col}")

            # Backward compatibility for older test/catalog fixtures.
            for src in metric.get("data_sources", []):
                dataset = src.get("dataset", "Unknown")
                if dataset not in source_datasets:
                    source_datasets.append(dataset)
                for col in src.get("required_columns", []):
                    required_columns.append(f"{dataset}.{col}")

            lineage_status = "Valid"
            if not source_datasets:
                source_datasets = ["manual_inputs"]
                lineage_status = "Manual Input"

            lineage.append(
                {
                    "metric_name": metric.get("metric_name", metric.get("name", "Unknown")),
                    "display_name": metric.get(
                        "display_name",
                        metric.get("metric_name", metric.get("name", "Unknown")),
                    ),
                    "category": metric.get("category", "Unknown"),
                    "source_datasets": ", ".join(sorted(set(source_datasets))),
                    "required_columns": ", ".join(sorted(set(required_columns))),
                    "formula_description": metric.get(
                        "formula_description",
                        metric.get("formula", "Not provided"),
                    ),
                    "business_owner": metric.get("business_owner", "Unassigned"),
                    "business_purpose": metric.get("business_purpose", "Not provided"),
                    "risk_if_misread": metric.get("risk_if_misread", "Not documented"),
                    "lineage_status": lineage_status,
                }
            )
        return lineage

    def get_metric_lineage(
        self, metric_name: str, metric_catalog: Dict[str, Any]
    ) -> Dict[str, Any]:
        lineage_list = self.build_metric_lineage(metric_catalog)
        for lin in lineage_list:
            if lin["metric_name"] == metric_name:
                return lin
        return {}

    def validate_lineage_sources(
        self, metric_catalog: Dict[str, Any], available_datasets: List[str]
    ) -> List[Dict[str, Any]]:
        lineage_list = self.build_metric_lineage(metric_catalog)
        available_set = set(available_datasets)

        for lin in lineage_list:
            sources = (
                [s.strip() for s in lin["source_datasets"].split(",")]
                if lin["source_datasets"]
                else []
            )
            sources = [s for s in sources if s != "manual_inputs"]
            missing = [s for s in sources if s not in available_set]
            if missing:
                lin["lineage_status"] = f"Missing Source: {', '.join(missing)}"
        return lineage_list

    def build_lineage_table(self, metric_catalog: Dict[str, Any]) -> pd.DataFrame:
        lineage_list = self.build_metric_lineage(metric_catalog)
        if not lineage_list:
            return pd.DataFrame(
                columns=[
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
            )
        return pd.DataFrame(lineage_list)
