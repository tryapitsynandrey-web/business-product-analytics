from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pandas as pd

from adapters.data_writer import DataWriter
from adapters.sqlite_writer import SQLiteIfExists, SQLiteWriter
from models.schemas import OUTPUT_SCHEMAS

logger = logging.getLogger(__name__)

PROCESSED_ARTIFACTS = [
    "kpi_summary",
    "customer_360",
    "data_quality_scores",
    "health_scores",
    "intervention_plan",
]

EXPORT_ARTIFACTS = [
    "churn_risk_profiles",
    "revenue_leakage",
    "recommendations",
    "decision_traces",
    "metric_lineage",
]


def _get(container: Any, key: str, default: Any = None) -> Any:
    if hasattr(container, "get"):
        return container.get(key, default)
    return getattr(container, key, default)


class OutputSerializer:
    """Build and persist schema-controlled CSV/SQLite output artifacts."""

    def __init__(self, run_id: str | None = None, generated_at: str | None = None) -> None:
        self.run_id = run_id
        self.generated_at = generated_at

    def build_artifacts(self, analytics: Any, decision: Any) -> dict[str, pd.DataFrame]:
        artifacts: dict[str, pd.DataFrame] = {}

        kpi_rows = [
            {
                "metric_name": k.metric_name,
                "value": k.value,
                "grain": k.grain,
                "explanation": k.explanation,
            }
            for k in _get(analytics, "kpis", [])
        ]
        if kpi_rows:
            artifacts["kpi_summary"] = pd.DataFrame(kpi_rows)

        self._add_dataframe_artifact(artifacts, "customer_360", _get(decision, "customer_360"))

        dq_rows = [
            {
                "dataset": s.dataset,
                "completeness_score": s.completeness_score,
                "uniqueness_score": s.uniqueness_score,
                "validity_score": s.validity_score,
                "referential_integrity_score": s.referential_integrity_score,
                "overall_score": s.overall_score,
                "status": s.status,
                "business_risk": s.business_risk,
            }
            for s in _get(decision, "data_quality_scores", [])
        ]
        if dq_rows:
            artifacts["data_quality_scores"] = pd.DataFrame(dq_rows)

        self._add_dataframe_artifact(artifacts, "health_scores", _get(decision, "health_scores"))
        self._add_records_artifact(
            artifacts, "intervention_plan", _get(decision, "interventions", [])
        )

        risk_rows = [
            {
                "customer_id": p.customer_id,
                "risk_score": p.risk_score,
                "risk_band": p.risk_band.value,
                "drivers": " | ".join(p.drivers) if isinstance(p.drivers, list) else p.drivers,
                "revenue_at_risk": p.revenue_at_risk,
                "explanation": p.explanation,
            }
            for p in _get(analytics, "risk_profiles", [])
        ]
        if risk_rows:
            artifacts["churn_risk_profiles"] = pd.DataFrame(risk_rows)

        self._add_records_artifact(artifacts, "revenue_leakage", _get(analytics, "leakages", []))
        self._add_records_artifact(
            artifacts,
            "recommendations",
            _get(analytics, "recommendations", []),
        )
        self._add_records_artifact(
            artifacts, "decision_traces", _get(decision, "decision_traces", [])
        )
        self._add_dataframe_artifact(artifacts, "metric_lineage", _get(decision, "metric_lineage"))

        self._stamp_artifacts(artifacts)
        return artifacts

    def write_csv_artifacts(
        self,
        data_writer: DataWriter,
        artifacts: dict[str, pd.DataFrame],
    ) -> list[str]:
        written: list[str] = []
        for artifact_name in PROCESSED_ARTIFACTS:
            df = artifacts.get(artifact_name)
            if df is None or df.empty:
                continue
            path = data_writer.processed_dir / f"{artifact_name}.csv"
            data_writer.write_dataframe_with_schema(
                df,
                path,
                OUTPUT_SCHEMAS[artifact_name],
                artifact_name,
            )
            written.append(f"data/processed/{artifact_name}.csv")

        for artifact_name in EXPORT_ARTIFACTS:
            df = artifacts.get(artifact_name)
            if df is None or df.empty:
                continue
            path = data_writer.exports_dir / f"{artifact_name}.csv"
            data_writer.write_dataframe_with_schema(
                df,
                path,
                OUTPUT_SCHEMAS[artifact_name],
                artifact_name,
            )
            written.append(f"data/exports/{artifact_name}.csv")

        return written

    def write_sqlite_artifacts(
        self,
        db_path: Path | str,
        artifacts: dict[str, pd.DataFrame],
        if_exists: SQLiteIfExists,
    ) -> list[str]:
        writer = SQLiteWriter(db_path)
        tables = writer.write_artifacts(artifacts, if_exists=if_exists)
        return [f"sqlite://{table}" for table in tables]

    @staticmethod
    def _add_dataframe_artifact(
        artifacts: dict[str, pd.DataFrame],
        artifact_name: str,
        df: Any,
    ) -> None:
        if isinstance(df, pd.DataFrame) and not df.empty:
            artifacts[artifact_name] = df

    @staticmethod
    def _add_records_artifact(
        artifacts: dict[str, pd.DataFrame],
        artifact_name: str,
        records: Any,
    ) -> None:
        if records:
            artifacts[artifact_name] = pd.DataFrame(records)

    def _stamp_artifacts(self, artifacts: dict[str, pd.DataFrame]) -> None:
        if self.run_id is None and self.generated_at is None:
            return
        for artifact_name, df in list(artifacts.items()):
            stamped = df.copy()
            if self.run_id is not None:
                stamped["run_id"] = self.run_id
            if self.generated_at is not None:
                stamped["generated_at"] = self.generated_at
            artifacts[artifact_name] = stamped
