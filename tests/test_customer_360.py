"""
Tests for src/core/customer_360.py
"""

from __future__ import annotations

import pytest
import pandas as pd
from datetime import date, timedelta

from core.customer_360 import Customer360Engine
from models.enums import RiskBand
from models.risk_profile import ChurnRiskProfile


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_datasets(
    num_customers: int = 3,
    include_nps: bool = True,
    multi_period_usage: bool = False,
) -> dict:
    today = date.today()
    cids = [f"C{i}" for i in range(num_customers)]

    customers = pd.DataFrame({
        "customer_id": cids,
        "is_active": [True] * num_customers,
        "signup_date": [today - timedelta(days=60)] * num_customers,
        "segment": ["SMB"] * num_customers,
    })

    subscriptions = pd.DataFrame({
        "subscription_id": [f"S{i}" for i in range(num_customers)],
        "customer_id": cids,
        "status": ["Active"] * num_customers,
        "monthly_price": [100.0] * num_customers,
        "plan": ["Pro"] * num_customers,
    })

    transactions = pd.DataFrame({
        "transaction_id": [f"TX{i}" for i in range(num_customers)],
        "customer_id": cids,
        "subscription_id": [f"S{i}" for i in range(num_customers)],
        "amount": [100.0] * num_customers,
        "status": ["Success"] * num_customers,
    })

    if multi_period_usage:
        # Two distinct date periods
        p1 = pd.Timestamp(today - timedelta(days=30))
        p2 = pd.Timestamp(today - timedelta(days=10))
        usage_rows = []
        for cid in cids:
            usage_rows.append({"usage_id": f"U{cid}a", "customer_id": cid,
                                "date": p1, "logins": 20, "key_actions": 10, "features_used": 3})
            usage_rows.append({"usage_id": f"U{cid}b", "customer_id": cid,
                                "date": p2, "logins": 25, "key_actions": 12, "features_used": 4})
        product_usage = pd.DataFrame(usage_rows)
    else:
        product_usage = pd.DataFrame({
            "usage_id": [f"U{i}" for i in range(num_customers)],
            "customer_id": cids,
            "date": [pd.Timestamp(today - timedelta(days=10))] * num_customers,
            "logins": [20] * num_customers,
            "key_actions": [10] * num_customers,
            "features_used": [3] * num_customers,
        })

    if include_nps:
        nps_scores = pd.DataFrame({
            "score_id": [f"N{i}" for i in range(num_customers)],
            "customer_id": cids,
            "date": [pd.Timestamp(today - timedelta(days=5))] * num_customers,
            "score": [8] * num_customers,
        })
    else:
        nps_scores = pd.DataFrame(columns=["score_id", "customer_id", "date", "score"])

    support_tickets = pd.DataFrame({
        "ticket_id": [f"T{i}" for i in range(num_customers)],
        "customer_id": cids,
        "status": ["Closed"] * num_customers,
    })

    return {
        "customers": customers,
        "subscriptions": subscriptions,
        "transactions": transactions,
        "product_usage": product_usage,
        "support_tickets": support_tickets,
        "nps_scores": nps_scores,
    }


def _make_profiles(
    cids: list,
    band: RiskBand = RiskBand.LOW,
    drivers: list | None = None,
    revenue_at_risk: float = 0.0,
) -> list:
    return [
        ChurnRiskProfile(
            customer_id=cid,
            risk_score=0.2 if band == RiskBand.LOW else 0.7,
            risk_band=band,
            drivers=drivers or [],
            revenue_at_risk=revenue_at_risk,
            explanation="Test.",
        )
        for cid in cids
    ]


# ---------------------------------------------------------------------------
# One row per customer
# ---------------------------------------------------------------------------

class TestOneRowPerCustomer:
    def test_output_has_one_row_per_customer(self):
        datasets = _make_datasets(num_customers=4)
        engine = Customer360Engine(datasets, [], [])
        df = engine.build_customer_360_view()
        assert len(df) == 4

    def test_customer_ids_match_input(self):
        datasets = _make_datasets(num_customers=2)
        engine = Customer360Engine(datasets, [], [])
        df = engine.build_customer_360_view()
        assert set(df["customer_id"]) == {"C0", "C1"}


# ---------------------------------------------------------------------------
# Churn risk attached
# ---------------------------------------------------------------------------

class TestAttachChurnRisk:
    def test_churn_risk_score_attached_correctly(self):
        datasets = _make_datasets(num_customers=2)
        profiles = _make_profiles(
            ["C0"], band=RiskBand.CRITICAL, revenue_at_risk=500.0
        )
        engine = Customer360Engine(datasets, profiles, [])
        df = engine.build_customer_360_view()

        c0 = df[df["customer_id"] == "C0"].iloc[0]
        assert c0["churn_risk_band"] == "Critical"
        assert c0["revenue_at_risk"] == pytest.approx(500.0)

    def test_customer_without_profile_gets_low_defaults(self):
        datasets = _make_datasets(num_customers=2)
        profiles = _make_profiles(["C0"])
        engine = Customer360Engine(datasets, profiles, [])
        df = engine.build_customer_360_view()

        c1 = df[df["customer_id"] == "C1"].iloc[0]
        assert c1["churn_risk_band"] == "Low"
        assert c1["revenue_at_risk"] == pytest.approx(0.0)

    def test_main_driver_attached(self):
        datasets = _make_datasets(num_customers=1)
        profiles = [
            ChurnRiskProfile(
                customer_id="C0",
                risk_score=0.8,
                risk_band=RiskBand.CRITICAL,
                drivers=["Failed Payments", "Low NPS"],
                revenue_at_risk=300.0,
                explanation="Test.",
            )
        ]
        engine = Customer360Engine(datasets, profiles, [])
        df = engine.build_customer_360_view()
        assert df.iloc[0]["main_driver"] == "Failed Payments"


# ---------------------------------------------------------------------------
# Recommendations attached
# ---------------------------------------------------------------------------

class TestAttachRecommendations:
    def test_recommendation_title_attached_as_recommended_action(self):
        datasets = _make_datasets(num_customers=1)
        recs = [
            {
                "customer_id": "C0",
                "recommendation_title": "Executive Outreach",
                "category": "retention",
            }
        ]
        engine = Customer360Engine(datasets, [], recs)
        df = engine.build_customer_360_view()
        assert df.iloc[0]["recommended_action"] == "Executive Outreach"

    def test_customer_without_recommendation_gets_default(self):
        datasets = _make_datasets(num_customers=2)
        recs = [{"customer_id": "C0", "recommendation_title": "Outreach"}]
        engine = Customer360Engine(datasets, [], recs)
        df = engine.build_customer_360_view()
        c1 = df[df["customer_id"] == "C1"].iloc[0]
        assert c1["recommended_action"] == "No action required"


# ---------------------------------------------------------------------------
# Usage trend classification
# ---------------------------------------------------------------------------

class TestUsageTrend:
    def test_usage_trend_column_present(self):
        datasets = _make_datasets(num_customers=2, multi_period_usage=True)
        engine = Customer360Engine(datasets, [], [])
        df = engine.build_customer_360_view()
        assert "usage_trend" in df.columns

    def test_valid_trend_labels_only(self):
        datasets = _make_datasets(num_customers=3, multi_period_usage=True)
        engine = Customer360Engine(datasets, [], [])
        df = engine.build_customer_360_view()
        valid = {"Increasing", "Stable", "Declining", "No Data"}
        assert set(df["usage_trend"].dropna()).issubset(valid)

    def test_single_period_usage_returns_no_data(self):
        datasets = _make_datasets(num_customers=2, multi_period_usage=False)
        engine = Customer360Engine(datasets, [], [])
        df = engine.build_customer_360_view()
        # With only one unique date, trend should be No Data
        assert all(t == "No Data" for t in df["usage_trend"].values)

    def test_usage_trend_no_date_column_returns_no_data_per_customer(self):
        datasets = _make_datasets(num_customers=2)
        usage = datasets["product_usage"].drop(columns=["date"])
        engine = Customer360Engine(datasets, [], [])

        trend = engine.calculate_usage_trend(usage)

        assert trend["customer_id"].tolist() == ["C0", "C1"]
        assert trend["usage_trend"].tolist() == ["No Data", "No Data"]


# ---------------------------------------------------------------------------
# Missing NPS handled safely
# ---------------------------------------------------------------------------

class TestMissingNPS:
    def test_missing_nps_does_not_raise(self):
        datasets = _make_datasets(num_customers=2, include_nps=False)
        engine = Customer360Engine(datasets, [], [])
        df = engine.build_customer_360_view()
        assert len(df) == 2

    def test_latest_nps_is_null_when_no_scores(self):
        datasets = _make_datasets(num_customers=2, include_nps=False)
        engine = Customer360Engine(datasets, [], [])
        df = engine.build_customer_360_view()
        assert df["latest_nps"].isnull().all()

# ---------------------------------------------------------------------------
# Segmentation integration
# ---------------------------------------------------------------------------

class TestSegmentationIntegration:
    def test_segmentation_columns_additive(self):
        datasets = _make_datasets(num_customers=2)
        engine = Customer360Engine(datasets, [], [])
        df = engine.build_customer_360_view()
        
        from core.segmentation import SegmentationEngine
        seg_engine = SegmentationEngine()
        seg_df = seg_engine.assign_customer_segments(df)
        
        assert "revenue_segment" in seg_df.columns
        assert "usage_segment" in seg_df.columns
        assert "risk_segment" in seg_df.columns
        assert "nps_segment" in seg_df.columns
        
        # Original columns still present
        assert "customer_id" in seg_df.columns
        assert "latest_usage_frequency" in seg_df.columns
