import pandas as pd
from typing import Dict, Any, List


class ProductHealthScoreEngine:
    def calculate_area_score(
        self, value: float, healthy_threshold: float, risk_threshold: float, inverse: bool = False
    ) -> float:
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
                return 100.0 * (
                    1.0 - (value - healthy_threshold) / (risk_threshold - healthy_threshold)
                )
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
        configs: list[tuple[str, str, float, float, bool]] = [
            ("Customer Retention", "retention_rate", 0.90, 0.70, False),
            ("Customer Churn", "churn_rate", 0.05, 0.15, True),
            ("User Activation", "activation_rate", 0.80, 0.50, False),
            ("User Engagement", "nps", 8.0, 4.0, False),
            ("Support Load", "support_burden", 1.0, 3.0, True),
        ]

        for area, metric, healthy, risk, inverse in configs:
            val = metrics.get(metric)
            if val is not None and not pd.isna(val):
                score = self.calculate_area_score(val, healthy, risk, inverse)
                status = self.assign_status(score)
                results.append(
                    {
                        "area": area,
                        "score": float(score),
                        "status": status,
                        "explanation": f"{metric} is {val:.2f}",
                    }
                )
        return results

    def calculate_business_health_summary(self, metrics: Dict[str, float]) -> List[Dict[str, Any]]:
        results = []
        configs: list[tuple[str, str, float, float, bool]] = [
            ("Revenue Growth", "revenue_growth_rate", 0.10, 0.0, False),
            ("Revenue Leakage", "revenue_leakage_ratio", 0.02, 0.10, True),
            ("Data Quality", "data_quality_score", 0.95, 0.75, False),
        ]

        for area, metric, healthy, risk, inverse in configs:
            val = metrics.get(metric)
            if val is not None and not pd.isna(val):
                score = self.calculate_area_score(val, healthy, risk, inverse)
                status = self.assign_status(score)
                results.append(
                    {
                        "area": area,
                        "score": float(score),
                        "status": status,
                        "explanation": f"{metric} is {val:.2f}",
                    }
                )
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
