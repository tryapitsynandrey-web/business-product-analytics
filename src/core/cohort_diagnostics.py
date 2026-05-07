import pandas as pd
from typing import Dict, Any, List

class CohortDiagnosticsEngine:
    def calculate_cohort_delta(self, cohort_retention: pd.DataFrame, baseline_retention: float) -> pd.DataFrame:
        if cohort_retention.empty:
            return pd.DataFrame(columns=["cohort_month", "period_number", "retention_rate", "baseline_retention", "delta"])
            
        df = cohort_retention.copy()
        df["baseline_retention"] = float(baseline_retention)
        df["delta"] = df["retention_rate"] - df["baseline_retention"]
        return df

    def identify_weak_cohorts(self, cohort_retention: pd.DataFrame, baseline_retention: float) -> pd.DataFrame:
        df = self.calculate_cohort_delta(cohort_retention, baseline_retention)
        if df.empty:
            return pd.DataFrame(columns=["cohort_month", "period_number", "retention_rate", "baseline_retention", "delta", "status"])
            
        def get_status(delta):
            if delta <= -0.20:
                return "Critical"
            elif delta <= -0.10:
                return "Risk"
            elif delta <= -0.05:
                return "Watch"
            return "Healthy"
            
        df["status"] = df["delta"].apply(get_status)
        return df

    def diagnose_cohort_drivers(self, cohort_summary: pd.DataFrame, usage_data: pd.DataFrame = None, support_data: pd.DataFrame = None, nps_data: pd.DataFrame = None) -> pd.DataFrame:
        if cohort_summary.empty:
            return pd.DataFrame(columns=["cohort_month", "period_number", "retention_rate", "baseline_retention", "delta", "status", "likely_driver", "recommended_action"])
            
        df = cohort_summary.copy()
        df["likely_driver"] = "Unknown"
        df["recommended_action"] = "Conduct deeper cohort analysis"
        
        def diagnose(row):
            if row.get("status") == "Healthy":
                return "N/A", "Maintain current strategy"
                
            return "Low Engagement or Support Issues", "Investigate cohort onboarding"
            
        diagnoses = df.apply(diagnose, axis=1)
        df["likely_driver"] = [d[0] for d in diagnoses]
        df["recommended_action"] = [d[1] for d in diagnoses]
        
        return df

    def build_cohort_diagnostics(self, cohort_summary: pd.DataFrame, baseline_retention: float) -> pd.DataFrame:
        if cohort_summary.empty:
            return pd.DataFrame(columns=["cohort_month", "period_number", "retention_rate", "baseline_retention", "delta", "status", "likely_driver", "recommended_action"])
            
        weak = self.identify_weak_cohorts(cohort_summary, baseline_retention)
        diagnosed = self.diagnose_cohort_drivers(weak)
        
        return diagnosed[["cohort_month", "period_number", "retention_rate", "baseline_retention", "delta", "status", "likely_driver", "recommended_action"]]
