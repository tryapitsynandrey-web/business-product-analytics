"""
business_health — Business Health Analytics Engine.

Provides pure-function metric implementations across:
- profitability
- revenue health
- cash flow
- unit economics
- growth
- efficiency
- risk
- composite health scoring
"""

from .business_health_score import BusinessHealthScoreEngine
from . import profitability
from . import revenue_metrics
from . import cashflow
from . import unit_economics
from . import growth_metrics
from . import efficiency_metrics
from . import risk_metrics

__all__ = [
    "BusinessHealthScoreEngine",
    "profitability",
    "revenue_metrics",
    "cashflow",
    "unit_economics",
    "growth_metrics",
    "efficiency_metrics",
    "risk_metrics",
]
