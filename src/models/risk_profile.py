from dataclasses import dataclass
from typing import List
from models.enums import RiskBand


@dataclass
class ChurnRiskProfile:
    customer_id: str
    risk_score: float  # 0.0 to 1.0
    risk_band: RiskBand
    drivers: List[str]
    revenue_at_risk: float
    explanation: str
