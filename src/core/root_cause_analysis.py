import pandas as pd
from typing import Dict, Any, List, Optional


class RootCauseAnalysisEngine:
    def analyze_metric_change(
        self,
        metric_name: str,
        current_value: float,
        previous_value: float,
        drivers: Dict[str, float],
    ) -> List[Dict[str, Any]]:
        causes = []
        if previous_value == 0:
            return causes

        change = (current_value - previous_value) / abs(previous_value)
        if abs(change) < 0.05:
            return causes

        for driver_name, driver_value in drivers.items():
            if abs(driver_value) > 0.1:
                causes.append(
                    {
                        "cause": f"{driver_name} change",
                        "evidence": f"{metric_name} changed by {change:.1%}, and driver {driver_name} showed {driver_value:.1%} change.",
                        "severity": "High" if abs(change) > 0.2 else "Medium",
                        "confidence": "Medium",
                        "recommended_investigation": f"Investigate {driver_name} trends.",
                    }
                )
        return causes

    def analyze_churn_drivers(
        self,
        churn_summary: Dict[str, Any],
        support_summary: Optional[Dict[str, Any]] = None,
        usage_summary: Optional[Dict[str, Any]] = None,
        nps_summary: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        causes = []
        churn_rate = churn_summary.get("churn_rate", 0.0)

        if churn_rate < 0.05:
            return causes

        severity = "High" if churn_rate > 0.1 else "Medium"

        if support_summary and support_summary.get("support_burden", 0) > 2.0:
            causes.append(
                {
                    "cause": "High support burden",
                    "evidence": f"Support burden is {support_summary.get('support_burden'):.1f} tickets per user.",
                    "severity": severity,
                    "confidence": "High",
                    "recommended_investigation": "Analyze ticket categories for top churned users.",
                }
            )

        if usage_summary and usage_summary.get("engagement_drop_rate", 0) > 0.2:
            causes.append(
                {
                    "cause": "Engagement drop",
                    "evidence": f"Engagement drop rate is {usage_summary.get('engagement_drop_rate'):.1%}.",
                    "severity": severity,
                    "confidence": "High",
                    "recommended_investigation": "Identify which features are being abandoned.",
                }
            )

        if nps_summary and nps_summary.get("average_nps", 10) < 6:
            causes.append(
                {
                    "cause": "Low NPS",
                    "evidence": f"Average NPS is {nps_summary.get('average_nps'):.1f}.",
                    "severity": severity,
                    "confidence": "Medium",
                    "recommended_investigation": "Read verbatim comments from detractors.",
                }
            )

        if not causes:
            causes.append(
                {
                    "cause": "Unknown churn driver",
                    "evidence": f"Churn rate is {churn_rate:.1%}, but no primary drivers breached thresholds.",
                    "severity": severity,
                    "confidence": "Low",
                    "recommended_investigation": "Conduct exit interviews.",
                }
            )

        return causes

    def analyze_revenue_drop_drivers(
        self,
        revenue_summary: Dict[str, Any],
        refund_summary: Optional[Dict[str, Any]] = None,
        failed_payment_summary: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        causes = []
        growth = revenue_summary.get("revenue_growth_rate", 0.0)

        if growth >= 0:
            return causes

        severity = "Critical" if growth < -0.1 else "High"

        if refund_summary and refund_summary.get("refund_rate", 0) > 0.05:
            causes.append(
                {
                    "cause": "Elevated refunds",
                    "evidence": f"Refund rate is {refund_summary.get('refund_rate'):.1%}.",
                    "severity": severity,
                    "confidence": "High",
                    "recommended_investigation": "Review refund reasons.",
                }
            )

        if failed_payment_summary and failed_payment_summary.get("failed_payment_rate", 0) > 0.08:
            causes.append(
                {
                    "cause": "Failed payments",
                    "evidence": f"Failed payment rate is {failed_payment_summary.get('failed_payment_rate'):.1%}.",
                    "severity": severity,
                    "confidence": "High",
                    "recommended_investigation": "Check payment gateway integrations.",
                }
            )

        if not causes:
            causes.append(
                {
                    "cause": "Contraction or Churn",
                    "evidence": f"Revenue dropped by {-growth:.1%}, not driven by refunds or failures.",
                    "severity": severity,
                    "confidence": "Medium",
                    "recommended_investigation": "Analyze churn and contraction revenue metrics.",
                }
            )

        return causes

    def rank_root_causes(self, causes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        sev_map = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}
        conf_map = {"High": 3, "Medium": 2, "Low": 1}

        def sort_key(c):
            return (
                sev_map.get(c.get("severity", "Low"), 1),
                conf_map.get(c.get("confidence", "Low"), 1),
            )

        return sorted(causes, key=sort_key, reverse=True)

    def build_root_cause_summary(self, causes: List[Dict[str, Any]]) -> pd.DataFrame:
        if not causes:
            return pd.DataFrame(
                columns=["cause", "evidence", "severity", "confidence", "recommended_investigation"]
            )

        ranked = self.rank_root_causes(causes)
        return pd.DataFrame(ranked)
