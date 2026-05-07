from dataclasses import dataclass
from typing import List
from models.enums import InterventionType, RecommendationPriority

@dataclass
class BusinessRecommendation:
    recommendation_id: str
    intervention_type: InterventionType
    target_segment: str
    affected_customers: List[str]
    expected_revenue_protected: float
    expected_revenue_created: float
    effort_level: str  # 'Low', 'Medium', 'High'
    confidence: float  # 0.0 to 1.0
    priority_score: float
    suggested_owner: str
    implementation_rationale: str
