import pandas as pd
import pytest
from core.churn_analysis import ChurnAnalysisEngine

@pytest.fixture
def subscriptions():
    return pd.DataFrame([
        {'customer_id': '1', 'status': 'Active', 'plan': 'Pro', 'start_date': '2023-01-01', 'end_date': None},
        {'customer_id': '2', 'status': 'Canceled', 'plan': 'Basic', 'start_date': '2023-01-15', 'end_date': '2023-03-15'},
        {'customer_id': '3', 'status': 'Past Due', 'plan': 'Pro', 'start_date': '2023-02-01', 'end_date': None},
    ])

@pytest.fixture
def customers():
    return pd.DataFrame([
        {'customer_id': '1', 'segment': 'Enterprise'},
        {'customer_id': '2', 'segment': 'SMB'},
        {'customer_id': '3', 'segment': 'Mid-Market'},
    ])

def test_churn_rate_calculation():
    engine = ChurnAnalysisEngine()
    rate = engine.calculate_churn_rate(80, 20)
    assert rate == 0.2

def test_retention_rate_calculation():
    engine = ChurnAnalysisEngine()
    rate = engine.calculate_retention_rate(80, 20)
    assert rate == 0.8

def test_summarize_churn_health(subscriptions):
    engine = ChurnAnalysisEngine()
    summary = engine.summarize_churn_health(subscriptions)
    assert summary['active_customers'] == 2
    assert summary['churned_customers'] == 1
    assert summary['churn_rate'] == pytest.approx(0.333, rel=1e-2)

def test_churn_by_plan(subscriptions):
    engine = ChurnAnalysisEngine()
    df = engine.analyze_churn_by_plan(subscriptions)
    pro = df[df['plan'] == 'Pro'].iloc[0]
    assert pro['active_customers'] == 2
    assert pro['churned_customers'] == 0
    basic = df[df['plan'] == 'Basic'].iloc[0]
    assert basic['active_customers'] == 0
    assert basic['churned_customers'] == 1

def test_zero_active_customers():
    engine = ChurnAnalysisEngine()
    df = pd.DataFrame([{'customer_id': '1', 'status': 'Canceled', 'plan': 'Basic', 'start_date': '2023-01-15', 'end_date': '2023-03-15'}])
    summary = engine.summarize_churn_health(df)
    assert summary['active_customers'] == 0
    assert summary['churned_customers'] == 1
    assert summary['churn_rate'] == 1.0

def test_empty_input():
    engine = ChurnAnalysisEngine()
    df = pd.DataFrame()
    summary = engine.summarize_churn_health(df)
    assert summary['active_customers'] == 0
    assert summary['churn_rate'] == 0.0
