import pandas as pd
import pytest
from core.funnel_analysis import FunnelAnalysisEngine

@pytest.fixture
def customers():
    return pd.DataFrame([
        {'customer_id': '1', 'signup_date': '2023-01-01', 'is_activated': True, 'segment': 'SMB'},
        {'customer_id': '2', 'signup_date': '2023-01-02', 'is_activated': False, 'segment': 'Enterprise'},
        {'customer_id': '3', 'signup_date': '2023-01-03', 'is_activated': True, 'segment': 'SMB'}
    ])

@pytest.fixture
def product_usage():
    return pd.DataFrame([
        {'customer_id': '1', 'key_actions': 5},
        {'customer_id': '2', 'key_actions': 0},
        {'customer_id': '3', 'key_actions': 10}
    ])

@pytest.fixture
def subscriptions():
    return pd.DataFrame([
        {'customer_id': '1', 'status': 'Active', 'monthly_price': 100, 'end_date': None},
        {'customer_id': '3', 'status': 'Canceled', 'monthly_price': 50, 'end_date': '2023-01-10'}
    ])

def test_funnel_steps(customers, product_usage, subscriptions):
    engine = FunnelAnalysisEngine()
    steps = engine.calculate_funnel_steps(customers, product_usage, subscriptions)
    assert steps['Signup'] == 3
    assert steps['Activation'] == 2
    assert steps['Key Action'] == 2
    assert steps['Paid Conversion'] == 2
    assert steps['Month-1 Retention'] == 1

def test_step_conversion(customers, product_usage, subscriptions):
    engine = FunnelAnalysisEngine()
    steps = engine.calculate_funnel_steps(customers, product_usage, subscriptions)
    df = engine.calculate_step_conversion(steps)
    
    act = df[df['step'] == 'Activation'].iloc[0]
    assert act['conversion_rate'] == pytest.approx(0.666, rel=1e-2)
    assert act['dropoff_rate'] == pytest.approx(0.333, rel=1e-2)

def test_largest_bottleneck(customers, product_usage, subscriptions):
    engine = FunnelAnalysisEngine()
    steps = engine.calculate_funnel_steps(customers, product_usage, subscriptions)
    df = engine.calculate_step_conversion(steps)
    bn = engine.identify_largest_bottleneck(df)
    assert bn['step'] in ['Month-1 Retention', 'Activation']

def test_segment_funnel(customers, product_usage, subscriptions):
    engine = FunnelAnalysisEngine()
    df = engine.calculate_segment_funnel(customers, product_usage, subscriptions)
    smb = df[df['segment'] == 'SMB']
    assert len(smb) == 5
    assert smb[smb['step'] == 'Signup']['users'].iloc[0] == 2

def test_zero_users():
    engine = FunnelAnalysisEngine()
    steps = engine.calculate_funnel_steps(pd.DataFrame(), pd.DataFrame(), pd.DataFrame())
    assert steps['Signup'] == 0
    df = engine.calculate_step_conversion(steps)
    assert df['conversion_rate'].sum() == 1.0
