from dataclasses import dataclass
from datetime import date
from models.enums import Segment

@dataclass
class CustomerProfile:
    customer_id: str
    company_name: str
    segment: Segment
    country: str
    signup_date: date
    acquisition_channel: str
    is_active: bool
    ltv: float = 0.0
    current_mrr: float = 0.0
