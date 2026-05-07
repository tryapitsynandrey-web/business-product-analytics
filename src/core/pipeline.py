"""
ProductAnalyticsPipeline — Orchestrator for the ProductPulse decision engine.

Responsibility:
    Load config → optionally generate synthetic data → load datasets →
    validate (with failure gate) → run Phase 2 analytics engines →
    run Phase 3 decision layer → write all outputs.

No business logic lives here.  This module wires together adapters, engines,
and the validation layer in a deterministic, logged sequence.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import yaml

from adapters.data_loader import DataLoader
from adapters.data_writer import DataWriter
from adapters.synthetic_data_generator import SyntheticDataGenerator
from core.metric_governance import MetricGovernance
from core.kpi_engine import KPIEngine
from core.churn_risk import ChurnRiskEngine
from core.revenue_leakage import RevenueLeakageEngine
from core.recommendation_engine import RecommendationEngine
from core.customer_360 import Customer360Engine
from core.decision_trace import DecisionTraceEngine
from core.prioritization import rank_interventions, rank_recommendations
from core.intervention_planner import InterventionPlanner
from core.data_quality_score import DataQualityScorer
from core.report_generator import ReportGenerator
from core.segmentation import SegmentationEngine
from core.metric_lineage import MetricLineageEngine
from core.health_score import ProductHealthScoreEngine
from models.schemas import OUTPUT_SCHEMAS
from utils.paths import PROJECT_ROOT, SQLITE_DB_PATH
from utils.validation import ValidationResult, run_dataset_validation
from adapters.sqlite_writer import SQLiteWriter


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class PipelineResult:
    """Structured outcome of a pipeline run."""
    success: bool
    validation_passed: bool
    outputs_written: bool
    message: str
    issues: List[str] = field(default_factory=list)
    generated_outputs: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Config loader
# ---------------------------------------------------------------------------

def _load_config(config_path: Path) -> Dict[str, Any]:
    """Parse config/config.yaml and return as a plain dict."""
    if not config_path.exists():
        raise FileNotFoundError(
            f"Configuration file not found: {config_path}. "
            "Ensure config/config.yaml exists before running the pipeline."
        )
    with config_path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


# ---------------------------------------------------------------------------
# Pipeline class
# ---------------------------------------------------------------------------

class ProductAnalyticsPipeline:
    """
    Orchestrates the end-to-end ProductPulse analytics run.

    Parameters
    ----------
    config_path : Path, optional
        Override the default config file location.
    """

    def __init__(self, config_path: Path | None = None) -> None:
        resolved_path = config_path or (PROJECT_ROOT / "config" / "config.yaml")
        self.config: Dict[str, Any] = _load_config(resolved_path)

        # Logging
        log_cfg = self.config.get("logging", {})
        log_level = getattr(logging, log_cfg.get("level", "INFO").upper(), logging.INFO)
        log_format = log_cfg.get(
            "format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        logging.basicConfig(level=log_level, format=log_format)
        self.logger = logging.getLogger(__name__)

        # Pipeline feature flags
        pipeline_cfg = self.config.get("pipeline", {})
        self._generate_synthetic: bool = pipeline_cfg.get("generate_synthetic_data", True)
        self._run_validation: bool = pipeline_cfg.get("run_validation", True)
        self._write_outputs: bool = pipeline_cfg.get("write_outputs", True)

        persistence_cfg = self.config.get("persistence", {}).get("sqlite", {})
        self._sqlite_enabled: bool = persistence_cfg.get("enabled", False)
        self._sqlite_path: str = persistence_cfg.get("path", str(SQLITE_DB_PATH))
        self._sqlite_if_exists: str = persistence_cfg.get("if_exists", "replace")

        # Reproducibility seed
        self._seed: int = self.config.get("reproducibility", {}).get("random_seed", 42)

        # Required datasets from config
        self._required_datasets: List[str] = self.config.get("required_datasets", [])

        # Adapters
        self.data_loader = DataLoader()
        self.data_writer = DataWriter()

        # Phase 2 engines
        self.governance = MetricGovernance()
        self.kpi_engine = KPIEngine(self.governance)
        self.churn_risk = ChurnRiskEngine()
        self.leakage = RevenueLeakageEngine()
        self.recommendations = RecommendationEngine()

        # Phase 3 engines
        self.intervention_planner = InterventionPlanner()
        self.reporter = ReportGenerator()

    # ------------------------------------------------------------------
    # Internal phase methods
    # ------------------------------------------------------------------

    def _phase_generate_synthetic(self) -> None:
        """Generate synthetic SaaS data and persist to data/synthetic/."""
        self.logger.info("Phase: generating synthetic data (seed=%d).", self._seed)
        num_customers = (
            self.config.get("synthetic_data", {}).get("num_customers", 1000)
        )
        generator = SyntheticDataGenerator(
            seed=self._seed, num_customers=num_customers
        )
        generator.generate_all()
        self.logger.info("Synthetic data generation complete.")

    def _phase_load(self) -> Dict[str, Any]:
        """Load all required datasets through the DataLoader adapter."""
        self.logger.info("Phase: loading datasets.")
        datasets = self.data_loader.load_all(
            required_datasets=self._required_datasets or None
        )
        self.logger.info(
            "Loaded %d dataset(s): %s.", len(datasets), ", ".join(datasets.keys())
        )
        return datasets

    def _phase_validate(self, datasets: Dict[str, Any]) -> ValidationResult:
        """Run the full validation suite; log each error/warning."""
        self.logger.info("Phase: validating datasets.")
        result = run_dataset_validation(datasets, self.config)

        for issue in result.issues:
            level = logging.ERROR if issue.severity == "error" else logging.WARNING
            self.logger.log(
                level,
                "[%s] %s — %s",
                issue.dataset,
                issue.check_name,
                issue.message,
            )

        if result.passed:
            self.logger.info(
                "Validation passed: %d check(s) run, 0 blocking errors.",
                result.total_checks,
            )
        else:
            self.logger.error(
                "Validation FAILED: %d check(s) run, %d failed.",
                result.total_checks,
                result.failed_checks,
            )
        return result

    def _phase_analytics(self, datasets: Dict[str, Any]) -> Dict[str, Any]:
        """Execute Phase 2 analytics engines in dependency order."""
        target_date = date.today()

        self.logger.info("Phase 2: calculating KPIs.")
        kpis = self.kpi_engine.calculate_kpis(datasets, target_date)
        for kpi in kpis:
            self.logger.info("KPI  %-30s = %s", kpi.metric_name, kpi.value)

        self.logger.info("Phase 2: evaluating churn risk.")
        risk_profiles = self.churn_risk.evaluate_risk(datasets)
        high_critical = [
            p for p in risk_profiles if p.risk_band.value in ("High", "Critical")
        ]
        self.logger.info(
            "Churn risk: %d high/critical customer(s) identified.", len(high_critical)
        )

        # Supplement KPIs with revenue_at_risk now that churn IDs are known
        high_risk_ids = [p.customer_id for p in high_critical]
        rar = self.kpi_engine.calculate_revenue_at_risk(
            datasets, target_date, high_risk_customer_ids=high_risk_ids
        )
        kpis.append(rar)
        self.logger.info("KPI  %-30s = %s", rar.metric_name, rar.value)

        self.logger.info("Phase 2: detecting revenue leakage.")
        leakages = self.leakage.detect_leakage(datasets)
        self.logger.info("Revenue leakage: %d event(s) detected.", len(leakages))

        self.logger.info("Phase 2: generating recommendations.")
        recs = self.recommendations.generate_recommendations(
            datasets, risk_profiles, leakages=leakages
        )
        recs = rank_recommendations(recs)
        self.logger.info("Recommendations: %d generated.", len(recs))

        return {
            "kpis": kpis,
            "risk_profiles": risk_profiles,
            "leakages": leakages,
            "recommendations": recs,
        }

    def _phase_decision_layer(
        self,
        datasets: Dict[str, Any],
        analytics: Dict[str, Any],
        validation_issues: List[Any],
    ) -> Dict[str, Any]:
        """Execute Phase 3: decision layer, Customer 360, tracing, interventions."""

        # Data quality scoring
        self.logger.info("Phase 3: scoring data quality.")
        primary_keys_cfg = self.config.get("primary_keys", {})

        dq_scorer = DataQualityScorer(
            issues=validation_issues,
            datasets=datasets,
            primary_keys=primary_keys_cfg,
        )
        dq_scores = dq_scorer.generate_quality_summary()

        # Customer 360
        self.logger.info("Phase 3: building Customer 360 view.")
        c360_engine = Customer360Engine(
            datasets=datasets,
            risk_profiles=analytics["risk_profiles"],
            recommendations=analytics["recommendations"],
        )
        customer_360_df = c360_engine.build_customer_360_view()
        
        self.logger.info("Phase 3: segmenting customers.")
        seg_engine = SegmentationEngine()
        customer_360_df = seg_engine.assign_customer_segments(customer_360_df)
        self.logger.info("Customer 360: %d rows built.", len(customer_360_df))

        # Intervention planning
        self.logger.info("Phase 3: creating intervention plan.")
        interventions = self.intervention_planner.create_intervention_plan(
            analytics["recommendations"]
        )
        interventions = rank_interventions(interventions)
        self.logger.info("Interventions: %d planned.", len(interventions))

        # Decision traces
        self.logger.info("Phase 3: generating decision traces.")
        tracer = DecisionTraceEngine()
        tracer.trace_all_churn_risks(analytics["risk_profiles"])
        tracer.trace_all_leakages(analytics["leakages"])
        tracer.trace_all_recommendations(analytics["recommendations"])
        tracer.trace_all_interventions(interventions)
        traces = tracer.export_traces()
        self.logger.info("Decision traces: %d recorded.", len(traces))

        # Metric Lineage
        self.logger.info("Phase 3: building metric lineage.")
        lineage_engine = MetricLineageEngine()
        metric_lineage_df = lineage_engine.build_lineage_table(self.governance._catalog)

        # Health Scores
        self.logger.info("Phase 3: calculating health scores.")
        health_engine = ProductHealthScoreEngine()
        
        metrics_dict = {k.metric_name: k.value for k in analytics.get("kpis", [])}
        overall_dq = [s.overall_score for s in dq_scores]
        if overall_dq:
            metrics_dict["data_quality_score"] = sum(overall_dq) / len(overall_dq)
            
        health_scores_df = health_engine.build_health_score_table(metrics_dict)

        return {
            "data_quality_scores": dq_scores,
            "customer_360": customer_360_df,
            "interventions": interventions,
            "decision_traces": traces,
            "metric_lineage": metric_lineage_df,
            "health_scores": health_scores_df,
        }

    def _phase_write_outputs(
        self,
        analytics: Dict[str, Any],
        decision: Dict[str, Any],
    ) -> List[str]:
        """Persist all analytics and decision layer outputs."""
        self.logger.info("Phase: writing outputs.")
        written: List[str] = []

        # ── data/processed/ ──────────────────────────────────────────────

        # KPI summary
        kpi_rows = [
            {
                "metric_name": k.metric_name,
                "value": k.value,
                "grain": k.grain,
                "explanation": k.explanation,
            }
            for k in analytics["kpis"]
        ]
        if kpi_rows:
            self.data_writer.write_dataframe_with_schema(
                pd.DataFrame(kpi_rows),
                self.data_writer.processed_dir / "kpi_summary.csv",
                OUTPUT_SCHEMAS["kpi_summary"],
                "kpi_summary"
            )
            written.append("data/processed/kpi_summary.csv")

        # Customer 360
        c360_df = decision.get("customer_360")
        if c360_df is not None and not c360_df.empty:
            self.data_writer.write_dataframe_with_schema(
                c360_df,
                self.data_writer.processed_dir / "customer_360.csv",
                OUTPUT_SCHEMAS["customer_360"],
                "customer_360"
            )
            written.append("data/processed/customer_360.csv")

        # Data quality scores
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
            for s in decision.get("data_quality_scores", [])
        ]
        if dq_rows:
            self.data_writer.write_dataframe_with_schema(
                pd.DataFrame(dq_rows),
                self.data_writer.processed_dir / "data_quality_scores.csv",
                OUTPUT_SCHEMAS["data_quality_scores"],
                "data_quality_scores"
            )
            written.append("data/processed/data_quality_scores.csv")

        # Health Scores
        health_scores_df = decision.get("health_scores")
        if health_scores_df is not None and not health_scores_df.empty:
            self.data_writer.write_dataframe_with_schema(
                health_scores_df,
                self.data_writer.processed_dir / "health_scores.csv",
                OUTPUT_SCHEMAS["health_scores"],
                "health_scores"
            )
            written.append("data/processed/health_scores.csv")

        # Intervention plan
        interventions = decision.get("interventions", [])
        if interventions:
            self.data_writer.write_dataframe_with_schema(
                pd.DataFrame(interventions),
                self.data_writer.processed_dir / "intervention_plan.csv",
                OUTPUT_SCHEMAS["intervention_plan"],
                "intervention_plan"
            )
            written.append("data/processed/intervention_plan.csv")

        # ── data/exports/ ────────────────────────────────────────────────

        # Churn risk profiles
        risk_rows = [
            {
                "customer_id": p.customer_id,
                "risk_score": p.risk_score,
                "risk_band": p.risk_band.value,
                "drivers": " | ".join(p.drivers),
                "revenue_at_risk": p.revenue_at_risk,
                "explanation": p.explanation,
            }
            for p in analytics["risk_profiles"]
        ]
        if risk_rows:
            self.data_writer.write_dataframe_with_schema(
                pd.DataFrame(risk_rows),
                self.data_writer.exports_dir / "churn_risk_profiles.csv",
                OUTPUT_SCHEMAS["churn_risk_profiles"],
                "churn_risk_profiles"
            )
            written.append("data/exports/churn_risk_profiles.csv")

        # Revenue leakage
        if analytics["leakages"]:
            self.data_writer.write_dataframe_with_schema(
                pd.DataFrame(analytics["leakages"]),
                self.data_writer.exports_dir / "revenue_leakage.csv",
                OUTPUT_SCHEMAS["revenue_leakage"],
                "revenue_leakage"
            )
            written.append("data/exports/revenue_leakage.csv")

        # Recommendations
        if analytics["recommendations"]:
            self.data_writer.write_dataframe_with_schema(
                pd.DataFrame(analytics["recommendations"]),
                self.data_writer.exports_dir / "recommendations.csv",
                OUTPUT_SCHEMAS["recommendations"],
                "recommendations"
            )
            written.append("data/exports/recommendations.csv")

        # Decision traces
        traces = decision.get("decision_traces", [])
        if traces:
            self.data_writer.write_dataframe_with_schema(
                pd.DataFrame(traces),
                self.data_writer.exports_dir / "decision_traces.csv",
                OUTPUT_SCHEMAS["decision_traces"],
                "decision_traces"
            )
            written.append("data/exports/decision_traces.csv")

        # Metric Lineage
        metric_lineage_df = decision.get("metric_lineage")
        if metric_lineage_df is not None and not metric_lineage_df.empty:
            self.data_writer.write_dataframe_with_schema(
                metric_lineage_df,
                self.data_writer.exports_dir / "metric_lineage.csv",
                OUTPUT_SCHEMAS["metric_lineage"],
                "metric_lineage"
            )
            written.append("data/exports/metric_lineage.csv")

        # ── reports/ ─────────────────────────────────────────────────────

        # Merge results for reporter
        full_results = {**analytics, **decision}

        self.logger.info("Phase: generating reports.")

        self.reporter.generate_executive_summary(full_results)
        written.append("reports/executive_summary.md")

        self.reporter.generate_data_quality_report(
            decision.get("data_quality_scores", [])
        )
        written.append("reports/data_quality_report.md")

        self.reporter.generate_intervention_plan(interventions)
        written.append("reports/intervention_plan.md")

        self.reporter.generate_risk_register(analytics)
        written.append("reports/risk_register.md")

        # Metric definitions from governance catalog
        catalog = self.governance._catalog
        if catalog:
            self.reporter.generate_metric_definitions(catalog)
            written.append("reports/metric_definitions.md")

        return written

    def _phase_write_sqlite_outputs(
        self, analytics: Dict[str, Any], decision: Dict[str, Any]
    ) -> List[str]:
        """Write schema-controlled artifacts to local SQLite database."""
        self.logger.info("Phase: writing SQLite outputs to %s.", self._sqlite_path)
        writer = SQLiteWriter(self._sqlite_path)
        
        # Build artifacts dict
        artifacts = {}
        
        # KPI Summary
        kpi_rows = [
            {
                "metric_name": k.metric_name,
                "value": k.value,
                "grain": k.grain,
                "explanation": k.explanation,
            }
            for k in analytics.get("kpis", [])
        ]
        if kpi_rows:
            artifacts["kpi_summary"] = pd.DataFrame(kpi_rows)
            
        # Health Scores
        health_scores_df = decision.get("health_scores")
        if health_scores_df is not None and not health_scores_df.empty:
            artifacts["health_scores"] = health_scores_df
            
        # Customer 360
        c360_df = decision.get("customer_360")
        if c360_df is not None and not c360_df.empty:
            artifacts["customer_360"] = c360_df
            
        # Data Quality Scores
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
            for s in decision.get("data_quality_scores", [])
        ]
        if dq_rows:
            artifacts["data_quality_scores"] = pd.DataFrame(dq_rows)
            
        # Intervention Plan
        interventions = decision.get("interventions", [])
        if interventions:
            artifacts["intervention_plan"] = pd.DataFrame(interventions)
            
        # Churn Risk Profiles
        risk_rows = [
            {
                "customer_id": p.customer_id,
                "risk_score": p.risk_score,
                "risk_segment": p.risk_segment,
                "revenue_at_risk": p.revenue_at_risk,
                "explanation": p.explanation,
            }
            for p in analytics.get("risk_profiles", [])
        ]
        if risk_rows:
            artifacts["churn_risk_profiles"] = pd.DataFrame(risk_rows)
            
        # Revenue Leakage
        if analytics.get("leakages"):
            artifacts["revenue_leakage"] = pd.DataFrame(analytics["leakages"])
            
        # Recommendations
        if analytics.get("recommendations"):
            artifacts["recommendations"] = pd.DataFrame(analytics["recommendations"])
            
        # Decision Traces
        traces = decision.get("decision_traces", [])
        if traces:
            artifacts["decision_traces"] = pd.DataFrame(traces)
            
        # Metric Lineage
        if decision.get("metric_lineage") is not None and not decision["metric_lineage"].empty:
            artifacts["metric_lineage"] = decision["metric_lineage"]
            
        try:
            tables = writer.write_artifacts(artifacts, if_exists=self._sqlite_if_exists)
            return [f"sqlite://{table}" for table in tables]
        except Exception as e:
            self.logger.error("Failed to write SQLite outputs: %s", e)
            return []

    # ------------------------------------------------------------------
    # Public run method
    # ------------------------------------------------------------------

    def run(self) -> PipelineResult:
        """
        Execute the full pipeline in sequential phases.

        Returns
        -------
        PipelineResult
            Structured result object; never raises unhandled exceptions.
        """
        self.logger.info("=" * 60)
        self.logger.info("ProductPulse Analytics Pipeline — starting.")
        self.logger.info("=" * 60)

        try:
            # Phase 1 — Synthetic data (optional)
            if self._generate_synthetic:
                self._phase_generate_synthetic()

            # Phase 2 — Load datasets
            datasets = self._phase_load()

            # Phase 3 — Validation gate
            validation_passed = True
            validation_issues: List[Any] = []
            if self._run_validation:
                val_result = self._phase_validate(datasets)
                validation_passed = val_result.passed
                validation_issues = val_result.issues
                if not validation_passed:
                    self.logger.error(
                        "Pipeline halted: validation errors must be resolved before "
                        "analytics can proceed."
                    )
                    return PipelineResult(
                        success=False,
                        validation_passed=False,
                        outputs_written=False,
                        message=(
                            f"Pipeline halted due to {val_result.failed_checks} "
                            "validation error(s). Review logs for details."
                        ),
                        issues=[i.message for i in val_result.issues if i.severity == "error"],
                    )

            # Phase 4 — Phase 2 analytics engines
            analytics = self._phase_analytics(datasets)

            # Phase 5 — Phase 3 decision layer
            decision = self._phase_decision_layer(
                datasets, analytics, validation_issues
            )

            # Phase 6 — Write outputs (optional)
            outputs_written = False
            generated_outputs: List[str] = []
            if self._write_outputs:
                generated_outputs = self._phase_write_outputs(analytics, decision)
                outputs_written = True

            # Phase 7 - SQLite Persistence (optional)
            if self._sqlite_enabled:
                sqlite_outputs = self._phase_write_sqlite_outputs(analytics, decision)
                generated_outputs.extend(sqlite_outputs)

            self.logger.info("=" * 60)
            self.logger.info("Pipeline completed successfully.")
            self.logger.info("=" * 60)

            return PipelineResult(
                success=True,
                validation_passed=validation_passed,
                outputs_written=outputs_written,
                message="Pipeline completed successfully.",
                generated_outputs=generated_outputs,
            )

        except FileNotFoundError as exc:
            self.logger.error("Data file missing: %s", exc)
            return PipelineResult(
                success=False,
                validation_passed=False,
                outputs_written=False,
                message=str(exc),
            )
        except Exception as exc:  # pylint: disable=broad-except
            self.logger.exception("Unexpected pipeline error: %s", exc)
            return PipelineResult(
                success=False,
                validation_passed=False,
                outputs_written=False,
                message=f"Unexpected error: {exc}",
            )
