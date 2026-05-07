from dataclasses import dataclass
from datetime import date
from typing import Optional, List, Dict

@dataclass
class MetricResult:
    metric_name: str
    value: float
    date_calculated: date
    grain: str  # e.g., 'Overall', 'Segment', 'Cohort'
    segment: Optional[str] = None
    is_anomaly: bool = False
    confidence_interval: Optional[tuple[float, float]] = None
    explanation: Optional[str] = None

@dataclass
class MetricRegistryEntry:
    metric_name: str
    display_name: str
    category: str
    source_datasets: List[str]
    required_columns_by_dataset: Dict[str, List[str]]
    business_owner: str
    business_purpose: str
    interpretation_notes: str
    risk_if_misread: str
    enabled: bool
    implementation_key: Optional[str]
    implementation_status: str

@dataclass
class MetricRegistryResult:
    entries: List[MetricRegistryEntry]
    mapped_count: int
    unmapped_count: int
    disabled_count: int
