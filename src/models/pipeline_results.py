from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

@dataclass
class PipelineResult:
    """Structured outcome of a pipeline run."""

    success: bool
    validation_passed: bool
    outputs_written: bool
    message: str
    issues: list[str] = field(default_factory=list)
    generated_outputs: list[str] = field(default_factory=list)



@dataclass
class AnalyticsResult:
    """Typed Phase 2 analytics output passed into the decision layer."""

    kpis: list[Any] = field(default_factory=list)
    risk_profiles: list[Any] = field(default_factory=list)
    leakages: list[dict[str, Any]] = field(default_factory=list)
    recommendations: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "kpis": self.kpis,
            "risk_profiles": self.risk_profiles,
            "leakages": self.leakages,
            "recommendations": self.recommendations,
        }

    def get(self, key: str, default: Any = None) -> Any:
        return self.as_dict().get(key, default)

    def __getitem__(self, key: str) -> Any:
        return self.as_dict()[key]


@dataclass
class DecisionLayerResult:
    """Typed Phase 3 decision-layer output passed into persistence and reports."""

    data_quality_scores: list[Any] = field(default_factory=list)
    customer_360: pd.DataFrame = field(default_factory=pd.DataFrame)
    interventions: list[dict[str, Any]] = field(default_factory=list)
    decision_traces: list[dict[str, Any]] = field(default_factory=list)
    metric_lineage: pd.DataFrame = field(default_factory=pd.DataFrame)
    health_scores: pd.DataFrame = field(default_factory=pd.DataFrame)
    scenario_analysis: pd.DataFrame = field(default_factory=pd.DataFrame)
    cohort_summary: pd.DataFrame = field(default_factory=pd.DataFrame)
    funnel_summary: pd.DataFrame = field(default_factory=pd.DataFrame)
    segment_funnel: pd.DataFrame = field(default_factory=pd.DataFrame)

    def as_dict(self) -> dict[str, Any]:
        return {
            "data_quality_scores": self.data_quality_scores,
            "customer_360": self.customer_360,
            "interventions": self.interventions,
            "decision_traces": self.decision_traces,
            "metric_lineage": self.metric_lineage,
            "health_scores": self.health_scores,
            "scenario_analysis": self.scenario_analysis,
            "cohort_summary": self.cohort_summary,
            "funnel_summary": self.funnel_summary,
            "segment_funnel": self.segment_funnel,
        }

    def get(self, key: str, default: Any = None) -> Any:
        return self.as_dict().get(key, default)

    def __getitem__(self, key: str) -> Any:
        return self.as_dict()[key]
