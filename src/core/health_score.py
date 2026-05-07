import pandas as pd
from typing import Dict, Any, List

class ProductHealthScoreEngine:
    def calculate_area_score(self, value: float, healthy_threshold: float, risk_threshold: float, inverse: bool = False) -> float:
        if pd.isna(value):
            return 0.0
            
        # inverse=True means lower is better (e.g. churn rate)
        if inverse:
            if value <= healthy_threshold:
                return 100.0
            elif value >= risk_threshold:
                return 0.0
            else:
                # linear interpolation
                return 100.0 * (1.0 - (value - healthy_threshold) / (risk_threshold - healthy_threshold))
        else:
            if value >= healthy_threshold:
                return 100.0
            elif value <= risk_threshold:
                return 0.0
            else:
                return 100.0 * ((value - risk_threshold) / (healthy_threshold - risk_threshold))

    def assign_status(self, score: float) -> str:
        if score >= 90:
            return "Healthy"
        elif score >= 70:
            return "Stable"
        elif score >= 50:
            return "Watch"
        elif score >= 30:
            return "Risk"
        return "Critical"

    def calculate_product_health_score(self, metrics: Dict[str, float]) -> List[Dict[str, Any]]:
        results = []
        
        # Define areas and their logic
        configs = [
            {"area": "Customer Retention", "metric": "retention_rate", "healthy": 0.90, "risk": 0.70, "inverse": False},
            {"area": "Customer Churn", "metric": "churn_rate", "healthy": 0.05, "risk": 0.15, "inverse": True},
            {"area": "User Activation", "metric": "activation_rate", "healthy": 0.80, "risk": 0.50, "inverse": False},
            {"area": "User Engagement", "metric": "nps", "healthy": 8.0, "risk": 4.0, "inverse": False},
            {"area": "Support Load", "metric": "support_burden", "healthy": 1.0, "risk": 3.0, "inverse": True}
        ]
        
        for conf in configs:
            val = metrics.get(conf["metric"])
            if val is not None and not pd.isna(val):
                score = self.calculate_area_score(val, conf["healthy"], conf["risk"], conf["inverse"])
                status = self.assign_status(score)
                results.append({
                    "area": conf["area"],
                    "score": float(score),
                    "status": status,
                    "explanation": f"{conf['metric']} is {val:.2f}"
                })
        return results

    def calculate_business_health_summary(self, metrics: Dict[str, float]) -> List[Dict[str, Any]]:
        results = []
        configs = [
            {"area": "Revenue Growth", "metric": "revenue_growth_rate", "healthy": 0.10, "risk": 0.0, "inverse": False},
            {"area": "Revenue Leakage", "metric": "revenue_leakage_ratio", "healthy": 0.02, "risk": 0.10, "inverse": True},
            {"area": "Data Quality", "metric": "data_quality_score", "healthy": 0.95, "risk": 0.75, "inverse": False}
        ]
        
        for conf in configs:
            val = metrics.get(conf["metric"])
            if val is not None and not pd.isna(val):
                score = self.calculate_area_score(val, conf["healthy"], conf["risk"], conf["inverse"])
                status = self.assign_status(score)
                results.append({
                    "area": conf["area"],
                    "score": float(score),
                    "status": status,
                    "explanation": f"{conf['metric']} is {val:.2f}"
                })
        return results

    def build_health_score_table(self, metrics: Dict[str, float]) -> pd.DataFrame:
        if not metrics:
            return pd.DataFrame(columns=["area", "score", "status", "explanation"])
            
        prod = self.calculate_product_health_score(metrics)
        biz = self.calculate_business_health_summary(metrics)
        
        all_res = prod + biz
        if not all_res:
            return pd.DataFrame(columns=["area", "score", "status", "explanation"])
            
        return pd.DataFrame(all_res)
