from enum import Enum

class Segment(str, Enum):
    ENTERPRISE = "Enterprise"
    MID_MARKET = "Mid-Market"
    SMB = "SMB"
    STARTUP = "Startup"

class Plan(str, Enum):
    BASIC = "Basic"
    PRO = "Pro"
    PREMIUM = "Premium"
    ENTERPRISE = "Enterprise"

class SubscriptionStatus(str, Enum):
    TRIAL = "Trial"
    ACTIVE = "Active"
    PAST_DUE = "Past Due"
    CANCELED = "Canceled"
    EXPIRED = "Expired"

class RiskBand(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"

class HealthStatus(str, Enum):
    HEALTHY = "Healthy"
    STABLE = "Stable"
    WATCH = "Watch"
    RISK = "Risk"
    CRITICAL = "Critical"
