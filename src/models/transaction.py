from dataclasses import dataclass
from datetime import datetime


@dataclass
class TransactionEvent:
    transaction_id: str
    customer_id: str
    subscription_id: str
    amount: float
    currency: str
    status: str  # 'Success', 'Failed', 'Refunded'
    transaction_date: datetime
    payment_method: str
