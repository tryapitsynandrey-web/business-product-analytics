from dataclasses import dataclass
from datetime import date
from typing import Optional
from models.enums import Plan, SubscriptionStatus

@dataclass
class SubscriptionState:
    subscription_id: str
    customer_id: str
    plan: Plan
    status: SubscriptionStatus
    start_date: date
    end_date: Optional[date]
    monthly_price: float
    billing_cycle: str
    auto_renew: bool
