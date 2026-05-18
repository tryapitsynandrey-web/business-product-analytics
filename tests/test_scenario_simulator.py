import pytest
from core.scenario_simulator import ScenarioSimulator


def test_churn_reduction_impact():
    simulator = ScenarioSimulator()
    res = simulator.simulate_churn_reduction(
        baseline_revenue=100000, churn_rate=0.05, improvement_rate=0.10
    )
    assert res["simulated_value"] == pytest.approx(0.045, rel=1e-5)
    assert res["monthly_impact"] == pytest.approx(500.0, rel=1e-5)


def test_activation_increase_impact():
    simulator = ScenarioSimulator()
    res = simulator.simulate_activation_increase(
        signups=1000, activation_rate=0.20, improvement_rate=0.10, arpu=50
    )
    assert res["simulated_value"] == pytest.approx(0.22, rel=1e-2)
    assert res["monthly_impact"] == pytest.approx(1000.0, rel=1e-2)


def test_arpu_increase_impact():
    simulator = ScenarioSimulator()
    res = simulator.simulate_arpu_increase(
        active_customers=1000, current_arpu=50, increase_rate=0.10
    )
    assert res["simulated_value"] == pytest.approx(55.0, rel=1e-5)
    assert res["monthly_impact"] == pytest.approx(5000.0, rel=1e-5)


def test_failed_payment_recovery():
    simulator = ScenarioSimulator()
    res = simulator.simulate_failed_payment_recovery(
        failed_payment_amount=10000, recovery_rate=0.30
    )
    assert res["simulated_value"] == 0.30
    assert res["monthly_impact"] == 3000.0


def test_margin_improvement():
    simulator = ScenarioSimulator()
    res = simulator.simulate_margin_improvement(
        revenue=100000, current_margin=0.70, improvement_points=0.05
    )
    assert res["simulated_value"] == 0.75
    assert res["monthly_impact"] == 5000.0


def test_annualized_impact():
    simulator = ScenarioSimulator()
    res = simulator.simulate_margin_improvement(
        revenue=100000, current_margin=0.70, improvement_points=0.05
    )
    assert res["annualized_impact"] == 60000.0


def test_run_default_scenarios():
    simulator = ScenarioSimulator()
    inputs = {
        "baseline_revenue": 100000,
        "churn_rate": 0.05,
        "signups": 1000,
        "activation_rate": 0.20,
        "arpu": 50,
        "active_customers": 1000,
        "current_arpu": 50,
        "failed_payment_amount": 10000,
        "revenue": 100000,
        "current_margin": 0.70,
    }
    df = simulator.run_default_scenarios(inputs)
    assert not df.empty
    assert len(df) == 5
    assert "scenario_name" in df.columns


def test_run_default_scenarios_returns_schema_when_no_inputs_match():
    simulator = ScenarioSimulator()

    df = simulator.run_default_scenarios({})

    assert df.empty
    assert df.columns.tolist() == [
        "scenario_name",
        "baseline_value",
        "simulated_value",
        "monthly_impact",
        "annualized_impact",
        "confidence_note",
    ]
