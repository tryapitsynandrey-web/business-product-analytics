import pandas as pd
import pytest
from core.revenue_analysis import RevenueAnalysisEngine

@pytest.fixture
def transactions():
    return pd.DataFrame([
        {'transaction_date': '2023-01-05', 'status': 'Success', 'amount': 100, 'customer_id': '1', 'subscription_id': 's1'},
        {'transaction_date': '2023-01-10', 'status': 'Refunded', 'amount': 20, 'customer_id': '2', 'subscription_id': 's2'},
        {'transaction_date': '2023-01-15', 'status': 'Failed', 'amount': 50, 'customer_id': '3', 'subscription_id': 's3'},
        {'transaction_date': '2023-02-05', 'status': 'Success', 'amount': 200, 'customer_id': '1', 'subscription_id': 's1'}
    ])

def test_paid_revenue_calculation(transactions):
    engine = RevenueAnalysisEngine()
    summary = engine.summarize_revenue_health(transactions)
    assert summary['gross_revenue'] == 300.0

def test_refunds_reduce_net_revenue(transactions):
    engine = RevenueAnalysisEngine()
    summary = engine.summarize_revenue_health(transactions)
    assert summary['net_revenue'] == 280.0

def test_failed_payments_tracked_separately(transactions):
    engine = RevenueAnalysisEngine()
    summary = engine.summarize_revenue_health(transactions)
    assert summary['failed_payment_rate'] == 50.0 / 300.0

def test_monthly_grouping(transactions):
    engine = RevenueAnalysisEngine()
    df = engine.analyze_revenue_by_month(transactions)
    assert len(df) == 2
    jan = df[df['period'] == '2023-01'].iloc[0]
    assert jan['gross_revenue'] == 100.0
    assert jan['refunds'] == 20.0
    assert jan['failed_payments'] == 50.0
    assert jan['net_revenue'] == 80.0

def test_empty_transactions():
    engine = RevenueAnalysisEngine()
    empty = pd.DataFrame()
    summary = engine.summarize_revenue_health(empty)
    assert summary['gross_revenue'] == 0.0
    
    df = engine.analyze_revenue_by_month(empty)
    assert df.empty
    assert 'period' in df.columns
