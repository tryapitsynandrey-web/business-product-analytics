import pytest
import pandas as pd
from core.segmentation import SegmentationEngine

@pytest.fixture
def c360():
    return pd.DataFrame([
        {"customer_id": "1", "mrr": 2000, "total_actions": 100, "churn_risk_score": 20, "latest_nps": 10},
        {"customer_id": "2", "mrr": 200, "total_actions": 20, "churn_risk_score": 45, "latest_nps": 8},
        {"customer_id": "3", "mrr": 50, "total_actions": 5, "churn_risk_score": 65, "latest_nps": 4},
        {"customer_id": "4", "mrr": 0, "total_actions": 0, "churn_risk_score": 85, "latest_nps": None}
    ])

def test_revenue_segmentation(c360):
    engine = SegmentationEngine()
    df = engine.segment_by_revenue(c360)
    segs = df["revenue_segment"].tolist()
    assert segs == ["Enterprise Value", "Mid Value", "Low Value", "No Revenue"]

def test_usage_segmentation(c360):
    engine = SegmentationEngine()
    df = engine.segment_by_usage(c360)
    segs = df["usage_segment"].tolist()
    assert segs == ["Power User", "Regular User", "Low Usage", "No Usage"]

def test_risk_segmentation(c360):
    engine = SegmentationEngine()
    df = engine.segment_by_risk(c360)
    segs = df["risk_segment"].tolist()
    assert segs == ["Low Risk", "Medium Risk", "High Risk", "Critical Risk"]

def test_nps_segmentation(c360):
    engine = SegmentationEngine()
    df = engine.segment_by_nps(c360)
    segs = df["nps_segment"].tolist()
    assert segs == ["Promoter", "Passive", "Detractor", "No NPS"]

def test_assign_customer_segments(c360):
    engine = SegmentationEngine()
    df = engine.assign_customer_segments(c360)
    assert "revenue_segment" in df.columns
    assert "usage_segment" in df.columns
    assert "risk_segment" in df.columns
    assert "nps_segment" in df.columns

def test_segment_summary(c360):
    engine = SegmentationEngine()
    df = engine.build_segment_summary(c360)
    assert not df.empty
    assert "segment_type" in df.columns
    assert df[df["segment_name"] == "Enterprise Value"]["customer_count"].iloc[0] == 1
    assert df[df["segment_name"] == "Enterprise Value"]["percentage"].iloc[0] == 0.25

def test_empty_dataframe_handling():
    engine = SegmentationEngine()
    df = engine.assign_customer_segments(pd.DataFrame())
    assert df.empty
    assert "revenue_segment" in df.columns
