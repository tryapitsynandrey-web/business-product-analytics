from dataclasses import dataclass

@dataclass
class ScenarioResult:
    scenario_name: str
    metric_affected: str
    baseline_value: float
    simulated_value: float
    monthly_impact: float
    annualized_impact: float
    confidence_note: str
