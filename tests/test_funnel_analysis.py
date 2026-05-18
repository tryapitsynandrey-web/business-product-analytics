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


def test_funnel_steps_activation_date_and_optional_inputs():
    engine = FunnelAnalysisEngine()
    customers = pd.DataFrame(
        [
            {"customer_id": "1", "signup_date": "2023-01-01", "activation_date": "2023-01-02"},
            {"customer_id": "2", "signup_date": "2023-01-02", "activation_date": None},
        ]
    )
    subscriptions = pd.DataFrame(
        [
            {"customer_id": "1", "status": "Active", "end_date": None},
            {"customer_id": "2", "status": "Active", "end_date": None},
        ]
    )

    steps = engine.calculate_funnel_steps(customers, pd.DataFrame(), subscriptions)

    assert steps["Activation"] == 1
    assert steps["Key Action"] == 0
    assert steps["Paid Conversion"] == 0

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


def test_largest_bottleneck_empty_or_single_row():
    engine = FunnelAnalysisEngine()

    assert engine.identify_largest_bottleneck(pd.DataFrame()) == {
        "step": "None",
        "dropoff_rate": 0.0,
    }
    assert engine.identify_largest_bottleneck(pd.DataFrame([{"step": "Signup"}])) == {
        "step": "None",
        "dropoff_rate": 0.0,
    }

def test_segment_funnel(customers, product_usage, subscriptions):
    engine = FunnelAnalysisEngine()
    df = engine.calculate_segment_funnel(customers, product_usage, subscriptions)
    smb = df[df['segment'] == 'SMB']
    assert len(smb) == 5
    assert smb[smb['step'] == 'Signup']['users'].iloc[0] == 2


def test_segment_funnel_handles_empty_and_missing_segment():
    engine = FunnelAnalysisEngine()
    no_segment = pd.DataFrame([{"customer_id": "1", "is_activated": True}])

    empty = engine.calculate_segment_funnel(pd.DataFrame(), pd.DataFrame(), pd.DataFrame())
    unknown = engine.calculate_segment_funnel(no_segment, pd.DataFrame(), pd.DataFrame())

    assert empty.empty
    assert unknown["segment"].unique().tolist() == ["Unknown"]


def test_segment_funnel_handles_no_groups_after_empty_override():
    class NonEmptyFrame(pd.DataFrame):
        @property
        def _constructor(self):
            return NonEmptyFrame

        @property
        def empty(self):
            return False

    engine = FunnelAnalysisEngine()
    customers = NonEmptyFrame(columns=["customer_id", "segment"])

    df = engine.calculate_segment_funnel(customers, pd.DataFrame(), pd.DataFrame())

    assert df.empty
    assert df.columns.tolist() == [
        "segment",
        "step",
        "users",
        "conversion_rate",
        "dropoff_rate",
        "previous_step_users",
    ]

def test_zero_users():
    engine = FunnelAnalysisEngine()
    steps = engine.calculate_funnel_steps(pd.DataFrame(), pd.DataFrame(), pd.DataFrame())
    assert steps['Signup'] == 0
    df = engine.calculate_step_conversion(steps)
    assert df['conversion_rate'].sum() == 1.0
