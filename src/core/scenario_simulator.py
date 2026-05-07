import pandas as pd
from typing import Dict, Any, List

class ScenarioSimulator:
    def simulate_churn_reduction(self, baseline_revenue: float, churn_rate: float, improvement_rate: float) -> Dict[str, Any]:
        new_churn_rate = churn_rate * (1 - improvement_rate)
        monthly_impact = baseline_revenue * churn_rate * improvement_rate
        return {
            'scenario_name': 'Churn Reduction',
            'baseline_value': float(churn_rate),
            'simulated_value': float(new_churn_rate),
            'monthly_impact': float(monthly_impact),
            'annualized_impact': float(monthly_impact * 12),
            'confidence_note': 'Assumes uniform revenue distribution among churned customers.'
        }

    def simulate_activation_increase(self, signups: int, activation_rate: float, improvement_rate: float, arpu: float) -> Dict[str, Any]:
        new_activation_rate = min(1.0, activation_rate * (1 + improvement_rate))
        extra_activations = signups * (new_activation_rate - activation_rate)
        monthly_impact = extra_activations * arpu
        return {
            'scenario_name': 'Activation Increase',
            'baseline_value': float(activation_rate),
            'simulated_value': float(new_activation_rate),
            'monthly_impact': float(monthly_impact),
            'annualized_impact': float(monthly_impact * 12),
            'confidence_note': 'Assumes new activated customers convert to paid at historical rates.'
        }

    def simulate_arpu_increase(self, active_customers: int, current_arpu: float, increase_rate: float) -> Dict[str, Any]:
        new_arpu = current_arpu * (1 + increase_rate)
        monthly_impact = active_customers * (new_arpu - current_arpu)
        return {
            'scenario_name': 'ARPU Increase',
            'baseline_value': float(current_arpu),
            'simulated_value': float(new_arpu),
            'monthly_impact': float(monthly_impact),
            'annualized_impact': float(monthly_impact * 12),
            'confidence_note': 'Assumes zero increased churn from price elasticity.'
        }

    def simulate_failed_payment_recovery(self, failed_payment_amount: float, recovery_rate: float) -> Dict[str, Any]:
        monthly_impact = failed_payment_amount * recovery_rate
        return {
            'scenario_name': 'Failed Payment Recovery',
            'baseline_value': 0.0,
            'simulated_value': float(recovery_rate),
            'monthly_impact': float(monthly_impact),
            'annualized_impact': float(monthly_impact * 12),
            'confidence_note': 'Based on implementing automated dunning.'
        }

    def simulate_margin_improvement(self, revenue: float, current_margin: float, improvement_points: float) -> Dict[str, Any]:
        new_margin = current_margin + improvement_points
        monthly_impact = revenue * improvement_points
        return {
            'scenario_name': 'Margin Improvement',
            'baseline_value': float(current_margin),
            'simulated_value': float(new_margin),
            'monthly_impact': float(monthly_impact),
            'annualized_impact': float(monthly_impact * 12),
            'confidence_note': 'Assumes revenue remains constant.'
        }

    def run_default_scenarios(self, inputs: Dict[str, float]) -> pd.DataFrame:
        results = []
        
        if all(k in inputs for k in ['baseline_revenue', 'churn_rate']):
            results.append(self.simulate_churn_reduction(inputs['baseline_revenue'], inputs['churn_rate'], 0.10))
            
        if all(k in inputs for k in ['signups', 'activation_rate', 'arpu']):
            results.append(self.simulate_activation_increase(int(inputs['signups']), inputs['activation_rate'], 0.10, inputs['arpu']))
            
        if all(k in inputs for k in ['active_customers', 'current_arpu']):
            results.append(self.simulate_arpu_increase(int(inputs['active_customers']), inputs['current_arpu'], 0.05))
            
        if 'failed_payment_amount' in inputs:
            results.append(self.simulate_failed_payment_recovery(inputs['failed_payment_amount'], 0.30))
            
        if all(k in inputs for k in ['revenue', 'current_margin']):
            results.append(self.simulate_margin_improvement(inputs['revenue'], inputs['current_margin'], 0.02))
            
        if not results:
            return pd.DataFrame(columns=['scenario_name', 'baseline_value', 'simulated_value', 'monthly_impact', 'annualized_impact', 'confidence_note'])
            
        return pd.DataFrame(results)
