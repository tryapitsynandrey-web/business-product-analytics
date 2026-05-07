import pandas as pd
import pytest
from core.cohort_analysis import CohortAnalysisEngine

@pytest.fixture
def customers():
    return pd.DataFrame([
        {'customer_id': '1', 'signup_date': '2023-01-05'},
        {'customer_id': '2', 'signup_date': '2023-01-20'},
        {'customer_id': '3', 'signup_date': '2023-02-15'}
    ])

@pytest.fixture
def subscriptions():
    return pd.DataFrame([
        {'customer_id': '1', 'start_date': '2023-01-05', 'end_date': None},
        {'customer_id': '2', 'start_date': '2023-01-20', 'end_date': '2023-03-20'},
        {'customer_id': '3', 'start_date': '2023-02-15', 'end_date': None}
    ])

@pytest.fixture
def transactions():
    return pd.DataFrame([
        {'customer_id': '1', 'transaction_date': '2023-01-05', 'amount': 100, 'status': 'Success'},
        {'customer_id': '1', 'transaction_date': '2023-02-05', 'amount': 100, 'status': 'Success'},
        {'customer_id': '2', 'transaction_date': '2023-01-20', 'amount': 50, 'status': 'Success'},
        {'customer_id': '3', 'transaction_date': '2023-02-15', 'amount': 200, 'status': 'Success'}
    ])

def test_build_signup_cohorts(customers):
    engine = CohortAnalysisEngine()
    df = engine.build_signup_cohorts(customers)
    assert len(df) == 3
    assert df[df['customer_id'] == '1']['cohort_month'].iloc[0] == '2023-01'

def test_calculate_cohort_retention(customers, subscriptions):
    engine = CohortAnalysisEngine()
    df = engine.calculate_cohort_retention(customers, subscriptions)
    assert len(df) > 0
    jan = df[(df['cohort_month'] == '2023-01') & (df['period_number'] == 0)]
    assert jan['customers_in_cohort'].iloc[0] == 2
    assert jan['retained_customers'].iloc[0] == 2
    
def test_calculate_cohort_revenue(customers, transactions):
    engine = CohortAnalysisEngine()
    df = engine.calculate_cohort_revenue(customers, transactions)
    jan_0 = df[(df['cohort_month'] == '2023-01') & (df['period_number'] == 0)]
    assert jan_0['revenue'].iloc[0] == 150
    assert jan_0['revenue_per_customer'].iloc[0] == 75.0

def test_build_cohort_summary(customers, subscriptions, transactions):
    engine = CohortAnalysisEngine()
    df = engine.build_cohort_summary(customers, subscriptions, transactions)
    jan_0 = df[(df['cohort_month'] == '2023-01') & (df['period_number'] == 0)]
    assert jan_0['customers_in_cohort'].iloc[0] == 2
    assert jan_0['retained_customers'].iloc[0] == 2
    assert jan_0['revenue'].iloc[0] == 150

def test_empty_input():
    engine = CohortAnalysisEngine()
    df = engine.build_cohort_summary(pd.DataFrame(), pd.DataFrame(), pd.DataFrame())
    assert df.empty
    assert 'cohort_month' in df.columns
