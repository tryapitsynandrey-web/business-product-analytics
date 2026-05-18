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
from adapters.output_serializer import OutputSerializer
from adapters.sqlite_writer import SQLiteIfExists
from adapters.synthetic_data_generator import SyntheticDataGenerator
from core.churn_risk import ChurnRiskEngine
from core.cohort_analysis import CohortAnalysisEngine
from core.customer_360 import Customer360Engine
from core.data_quality_score import DataQualityScorer
from core.decision_trace import DecisionTraceEngine
from core.funnel_analysis import FunnelAnalysisEngine
from core.health_score import ProductHealthScoreEngine
from core.intervention_planner import InterventionPlanner
from core.kpi_engine import KPIEngine
from core.metric_governance import MetricGovernance
from core.metric_lineage import MetricLineageEngine
from core.prioritization import rank_interventions, rank_recommendations
from core.recommendation_engine import RecommendationEngine
from core.report_generator import ReportGenerator
from core.revenue_leakage import RevenueLeakageEngine
from core.scenario_simulator import ScenarioSimulator
from core.segmentation import SegmentationEngine
from models.pipeline_results import AnalyticsResult, DecisionLayerResult
from utils.paths import PROJECT_ROOT, SQLITE_DB_PATH, ensure_directories
from utils.validation import ValidationResult, run_dataset_validation


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


def _resolve_project_path(path_value: str | Path) -> Path:
    """Resolve config paths relative to the project root unless absolute."""
    path = Path(path_value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def _parse_config_date(value: Any, default: date | None = None) -> date:
    """Parse an ISO date from config, falling back to default or today."""
    if value is None:
        return default or date.today()
    return pd.Timestamp(value).date()


def _parse_sqlite_if_exists(value: Any) -> SQLiteIfExists:
    """Validate the configured pandas SQLite table-write mode."""
    allowed: set[SQLiteIfExists] = {"append", "delete_rows", "fail", "replace"}
    if value in allowed:
        return value
    raise ValueError(
        "persistence.sqlite.if_exists must be one of: append, delete_rows, fail, replace"
    )


def _as_analytics_result(analytics: AnalyticsResult | Dict[str, Any]) -> AnalyticsResult:
    """Accept legacy dicts in unit tests while production uses typed results."""
    if isinstance(analytics, AnalyticsResult):
        return analytics
    return AnalyticsResult(
        kpis=analytics.get("kpis", []),
        risk_profiles=analytics.get("risk_profiles", []),
        leakages=analytics.get("leakages", []),
        recommendations=analytics.get("recommendations", []),
    )


def _as_decision_result(decision: DecisionLayerResult | Dict[str, Any]) -> DecisionLayerResult:
    """Accept legacy dicts in unit tests while production uses typed results."""
    if isinstance(decision, DecisionLayerResult):
        return decision
    return DecisionLayerResult(
        data_quality_scores=decision.get("data_quality_scores", []),
        customer_360=decision.get("customer_360", pd.DataFrame()),
        interventions=decision.get("interventions", []),
        decision_traces=decision.get("decision_traces", []),
        metric_lineage=decision.get("metric_lineage", pd.DataFrame()),
        health_scores=decision.get("health_scores", pd.DataFrame()),
        scenario_analysis=decision.get("scenario_analysis", pd.DataFrame()),
        cohort_summary=decision.get("cohort_summary", pd.DataFrame()),
        funnel_summary=decision.get("funnel_summary", pd.DataFrame()),
        segment_funnel=decision.get("segment_funnel", pd.DataFrame()),
    )


def _kpi_value(kpis: list[Any], metric_name: str) -> float | None:
    for kpi in kpis:
        if kpi.metric_name == metric_name:
            return float(kpi.value)
    return None


def _build_scenario_inputs(
    datasets: Dict[str, Any],
    analytics: AnalyticsResult,
) -> Dict[str, float]:
    customers = datasets.get("customers", pd.DataFrame())
    subscriptions = datasets.get("subscriptions", pd.DataFrame())

    mrr = _kpi_value(analytics.kpis, "monthly_recurring_revenue")
    churn_rate = _kpi_value(analytics.kpis, "customer_churn_rate")
    activation_rate = _kpi_value(analytics.kpis, "activation_rate")
    arpu = _kpi_value(analytics.kpis, "average_revenue_per_user")
    gross_margin = _kpi_value(analytics.kpis, "gross_margin")

    inputs: Dict[str, float] = {}
    if mrr is not None:
        inputs["baseline_revenue"] = mrr
        inputs["revenue"] = mrr
    if churn_rate is not None:
        inputs["churn_rate"] = churn_rate
    if activation_rate is not None:
        inputs["activation_rate"] = activation_rate
    if arpu is not None:
        inputs["arpu"] = arpu
        inputs["current_arpu"] = arpu
    if gross_margin is not None:
        inputs["current_margin"] = gross_margin
    if isinstance(customers, pd.DataFrame) and not customers.empty:
        inputs["signups"] = float(customers["customer_id"].nunique())
    if isinstance(subscriptions, pd.DataFrame) and not subscriptions.empty:
        active = subscriptions[subscriptions["status"].isin(["Active", "Past Due"])]
        inputs["active_customers"] = float(active["customer_id"].nunique())

    failed_payment_amount = sum(
        float(leakage.get("estimated_revenue_loss", 0.0))
        for leakage in analytics.leakages
        if leakage.get("leakage_type") == "Failed Payment"
    )
    if failed_payment_amount > 0:
        inputs["failed_payment_amount"] = failed_payment_amount

    return inputs


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

    def __init__(
        self,
        config_path: Path | None = None,
        *,
        data_loader: DataLoader | None = None,
        data_writer: DataWriter | None = None,
        governance: MetricGovernance | None = None,
        kpi_engine: KPIEngine | None = None,
        churn_risk: ChurnRiskEngine | None = None,
        leakage: RevenueLeakageEngine | None = None,
        recommendations: RecommendationEngine | None = None,
        intervention_planner: InterventionPlanner | None = None,
        reporter: ReportGenerator | None = None,
        output_serializer: OutputSerializer | None = None,
    ) -> None:
        resolved_path = config_path or (PROJECT_ROOT / "config" / "config.yaml")
        self.config: Dict[str, Any] = _load_config(resolved_path)
        self._config_dir = (
            resolved_path.parent
            if (resolved_path.parent / "metric_catalog.yaml").exists()
            else PROJECT_ROOT / "config"
        )

        # Logging
        log_cfg = self.config.get("logging", {})
        log_level = getattr(logging, log_cfg.get("level", "INFO").upper(), logging.INFO)
        log_format = log_cfg.get("format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        logging.basicConfig(level=log_level, format=log_format)
        self.logger = logging.getLogger(__name__)

        # Pipeline feature flags
        pipeline_cfg = self.config.get("pipeline", {})
        self._generate_synthetic: bool = pipeline_cfg.get("generate_synthetic_data", True)
        self._run_validation: bool = pipeline_cfg.get("run_validation", True)
        self._write_outputs: bool = pipeline_cfg.get("write_outputs", True)

        paths_cfg = self.config.get("paths", {})
        self._synthetic_data_dir = _resolve_project_path(
            paths_cfg.get("synthetic_data_dir", "data/synthetic")
        )
        self._processed_data_dir = _resolve_project_path(
            paths_cfg.get("processed_data_dir", "data/processed")
        )
        self._exports_dir = _resolve_project_path(paths_cfg.get("exports_dir", "data/exports"))
        self._reports_dir = _resolve_project_path(paths_cfg.get("reports_dir", "reports"))

        persistence_cfg = self.config.get("persistence", {}).get("sqlite", {})
        self._sqlite_enabled: bool = persistence_cfg.get("enabled", False)
        self._sqlite_path: str = str(
            _resolve_project_path(persistence_cfg.get("path", str(SQLITE_DB_PATH)))
        )
        self._sqlite_if_exists: SQLiteIfExists = _parse_sqlite_if_exists(
            persistence_cfg.get("if_exists", "replace")
        )
        ensure_directories(
            [
                self._synthetic_data_dir,
                self._processed_data_dir,
                self._exports_dir,
                self._reports_dir,
                Path(self._sqlite_path).parent,
            ]
        )

        # Reproducibility seed
        repro_cfg = self.config.get("reproducibility", {})
        self._seed: int = repro_cfg.get("random_seed", 42)
        self._as_of_date: date = _parse_config_date(repro_cfg.get("as_of_date"))

        # Required datasets from config
        self._required_datasets: List[str] = self.config.get("required_datasets", [])

        # Adapters
        self.data_loader = data_loader or DataLoader(data_dir=self._synthetic_data_dir)
        self.data_writer = data_writer or DataWriter(
            processed_dir=self._processed_data_dir,
            exports_dir=self._exports_dir,
            reports_dir=self._reports_dir,
        )
        self.output_serializer = output_serializer or OutputSerializer(
            run_id=f"productpulse-{self._as_of_date.isoformat()}",
            generated_at=f"{self._as_of_date.isoformat()}T00:00:00+00:00",
        )

        # Phase 2 engines
        self.governance = governance or MetricGovernance(
            catalog_path=self._config_dir / "metric_catalog.yaml"
        )
        self.kpi_engine = kpi_engine or KPIEngine(self.governance)
        self.churn_risk = churn_risk or ChurnRiskEngine(
            rules_path=self._config_dir / "churn_rules.yaml"
        )
        self.leakage = leakage or RevenueLeakageEngine()
        self.recommendations = recommendations or RecommendationEngine(
            rules_path=self._config_dir / "recommendation_rules.yaml"
        )

        # Phase 3 engines
        self.intervention_planner = intervention_planner or InterventionPlanner()
        self.reporter = reporter or ReportGenerator(
            reports_dir=self._reports_dir,
            generated_on=self._as_of_date,
        )

    # ------------------------------------------------------------------
    # Internal phase methods
    # ------------------------------------------------------------------

    def _phase_generate_synthetic(self) -> None:
        """Generate synthetic SaaS data and persist to data/synthetic/."""
        self.logger.info("Phase: generating synthetic data (seed=%d).", self._seed)
        num_customers = self.config.get("synthetic_data", {}).get("num_customers", 1000)
        generator = SyntheticDataGenerator(
            seed=self._seed,
            num_customers=num_customers,
            as_of_date=self._as_of_date,
            output_dir=self._synthetic_data_dir,
        )
        generator.generate_all()
        self.logger.info("Synthetic data generation complete.")

    def _phase_load(self) -> Dict[str, Any]:
        """Load all required datasets through the DataLoader adapter."""
        self.logger.info("Phase: loading datasets.")
        datasets = self.data_loader.load_all(required_datasets=self._required_datasets or None)
        self.logger.info("Loaded %d dataset(s): %s.", len(datasets), ", ".join(datasets.keys()))
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

    def _phase_analytics(self, datasets: Dict[str, Any]) -> AnalyticsResult:
        """Execute Phase 2 analytics engines in dependency order."""
        target_date = self._as_of_date

        self.logger.info("Phase 2: calculating KPIs.")
        kpis = self.kpi_engine.calculate_kpis(datasets, target_date)
        # revenue_at_risk depends on churn scoring; drop the standalone proxy
        # and append the churn-informed value below.
        kpis = [k for k in kpis if k.metric_name != "revenue_at_risk"]
        for kpi in kpis:
            self.logger.info("KPI  %-30s = %s", kpi.metric_name, kpi.value)

        self.logger.info("Phase 2: evaluating churn risk.")
        risk_profiles = self.churn_risk.evaluate_risk(datasets)
        high_critical = [p for p in risk_profiles if p.risk_band.value in ("High", "Critical")]
        self.logger.info("Churn risk: %d high/critical customer(s) identified.", len(high_critical))

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

        return AnalyticsResult(
            kpis=kpis,
            risk_profiles=risk_profiles,
            leakages=leakages,
            recommendations=recs,
        )

    def _phase_decision_layer(
        self,
        datasets: Dict[str, Any],
        analytics: AnalyticsResult | Dict[str, Any],
        validation_issues: List[Any],
    ) -> DecisionLayerResult:
        """Execute Phase 3: decision layer, Customer 360, tracing, interventions."""
        analytics_result = _as_analytics_result(analytics)

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
            risk_profiles=analytics_result.risk_profiles,
            recommendations=analytics_result.recommendations,
        )
        customer_360_df = c360_engine.build_customer_360_view()

        self.logger.info("Phase 3: segmenting customers.")
        seg_engine = SegmentationEngine()
        customer_360_df = seg_engine.assign_customer_segments(customer_360_df)
        self.logger.info("Customer 360: %d rows built.", len(customer_360_df))

        # Intervention planning
        self.logger.info("Phase 3: creating intervention plan.")
        interventions = self.intervention_planner.create_intervention_plan(
            analytics_result.recommendations
        )
        interventions = rank_interventions(interventions)
        self.logger.info("Interventions: %d planned.", len(interventions))

        # Decision traces
        self.logger.info("Phase 3: generating decision traces.")
        tracer = DecisionTraceEngine(created_at=f"{self._as_of_date.isoformat()}T00:00:00+00:00")
        tracer.trace_all_churn_risks(analytics_result.risk_profiles)
        tracer.trace_all_leakages(analytics_result.leakages)
        tracer.trace_all_recommendations(analytics_result.recommendations)
        tracer.trace_all_interventions(interventions)
        traces = tracer.export_traces()
        self.logger.info("Decision traces: %d recorded.", len(traces))

        # Metric Lineage
        self.logger.info("Phase 3: building metric lineage.")
        lineage_engine = MetricLineageEngine()
        metric_lineage_df = lineage_engine.build_lineage_table(self.governance.get_catalog())

        # Health Scores
        self.logger.info("Phase 3: calculating health scores.")
        health_engine = ProductHealthScoreEngine()

        metrics_dict = {k.metric_name: k.value for k in analytics_result.kpis}
        overall_dq = [s.overall_score for s in dq_scores]
        if overall_dq:
            metrics_dict["data_quality_score"] = sum(overall_dq) / len(overall_dq)

        health_scores_df = health_engine.build_health_score_table(metrics_dict)

        self.logger.info("Phase 3: running scenario simulations.")
        scenario_inputs = _build_scenario_inputs(datasets, analytics_result)
        scenario_analysis_df = ScenarioSimulator().run_default_scenarios(scenario_inputs)

        self.logger.info("Phase 3: calculating cohort retention and revenue.")
        cohort_engine = CohortAnalysisEngine(as_of_date=self._as_of_date)
        cohort_summary_df = cohort_engine.build_cohort_summary(
            datasets.get("customers", pd.DataFrame()),
            datasets.get("subscriptions", pd.DataFrame()),
            datasets.get("transactions", pd.DataFrame()),
        )

        self.logger.info("Phase 3: calculating activation funnel.")
        funnel_engine = FunnelAnalysisEngine()
        funnel_steps = funnel_engine.calculate_funnel_steps(
            datasets.get("customers", pd.DataFrame()),
            datasets.get("product_usage", pd.DataFrame()),
            datasets.get("subscriptions", pd.DataFrame()),
        )
        funnel_summary_df = funnel_engine.calculate_step_conversion(funnel_steps)
        segment_funnel_df = funnel_engine.calculate_segment_funnel(
            datasets.get("customers", pd.DataFrame()),
            datasets.get("product_usage", pd.DataFrame()),
            datasets.get("subscriptions", pd.DataFrame()),
        )

        return DecisionLayerResult(
            data_quality_scores=dq_scores,
            customer_360=customer_360_df,
            interventions=interventions,
            decision_traces=traces,
            metric_lineage=metric_lineage_df,
            health_scores=health_scores_df,
            scenario_analysis=scenario_analysis_df,
            cohort_summary=cohort_summary_df,
            funnel_summary=funnel_summary_df,
            segment_funnel=segment_funnel_df,
        )

    def _phase_write_outputs(
        self,
        analytics: AnalyticsResult | Dict[str, Any],
        decision: DecisionLayerResult | Dict[str, Any],
    ) -> List[str]:
        """Persist all analytics and decision layer outputs."""
        self.logger.info("Phase: writing outputs.")
        analytics_result = _as_analytics_result(analytics)
        decision_result = _as_decision_result(decision)

        artifacts = self.output_serializer.build_artifacts(analytics_result, decision_result)
        written = self.output_serializer.write_csv_artifacts(self.data_writer, artifacts)

        full_results = {**analytics_result.as_dict(), **decision_result.as_dict()}

        self.logger.info("Phase: generating reports.")

        self.reporter.generate_executive_summary(full_results)
        written.append("reports/executive_summary.md")

        self.reporter.generate_data_quality_report(decision_result.data_quality_scores)
        written.append("reports/data_quality_report.md")

        self.reporter.generate_intervention_plan(decision_result.interventions)
        written.append("reports/intervention_plan.md")

        self.reporter.generate_risk_register(analytics_result.as_dict())
        written.append("reports/risk_register.md")

        catalog = self.governance.get_catalog()
        if catalog:
            self.reporter.generate_metric_definitions(catalog)
            written.append("reports/metric_definitions.md")

        return written

    def _phase_write_sqlite_outputs(
        self,
        analytics: AnalyticsResult | Dict[str, Any],
        decision: DecisionLayerResult | Dict[str, Any],
    ) -> List[str]:
        """Write schema-controlled artifacts to local SQLite database."""
        self.logger.info("Phase: writing SQLite outputs to %s.", self._sqlite_path)
        analytics_result = _as_analytics_result(analytics)
        decision_result = _as_decision_result(decision)
        artifacts = self.output_serializer.build_artifacts(analytics_result, decision_result)
        try:
            return self.output_serializer.write_sqlite_artifacts(
                self._sqlite_path,
                artifacts,
                self._sqlite_if_exists,
            )
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
            decision = self._phase_decision_layer(datasets, analytics, validation_issues)

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
