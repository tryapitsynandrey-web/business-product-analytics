import pandas as pd
from typing import Dict, Any, List


class AnomalyDetectionEngine:
    def detect_percentage_deviation(
        self, series: pd.Series, baseline_window: int = 3, threshold: float = 0.2
    ) -> List[Dict[str, Any]]:
        results: list[dict[str, Any]] = []
        if len(series) < baseline_window + 1:
            return results

        series = series.dropna()
        for i in range(baseline_window, len(series)):
            actual = series.iloc[i]
            baseline = series.iloc[i - baseline_window : i].mean()

            if pd.isna(baseline) or baseline == 0:
                continue

            deviation = (actual - baseline) / abs(baseline)
            if abs(deviation) >= threshold:
                results.append(
                    {
                        "period": str(series.index[i]),
                        "actual_value": actual,
                        "baseline_value": baseline,
                        "deviation": deviation,
                        "severity": self._get_severity(abs(deviation), threshold),
                        "method": "percentage_deviation",
                    }
                )
        return results

    def detect_z_score_anomalies(
        self, series: pd.Series, threshold: float = 2.0
    ) -> List[Dict[str, Any]]:
        results: list[dict[str, Any]] = []
        if len(series) < 3:
            return results

        series = series.dropna()
        mean = series.mean()
        std = series.std()

        if pd.isna(std) or std == 0:
            return results

        for i in range(len(series)):
            actual = series.iloc[i]
            z_score = (actual - mean) / std
            if abs(z_score) >= threshold:
                results.append(
                    {
                        "period": str(series.index[i]),
                        "actual_value": actual,
                        "baseline_value": mean,
                        "deviation": z_score,
                        "severity": self._get_z_severity(abs(z_score), threshold),
                        "method": "z_score",
                    }
                )
        return results

    def detect_moving_average_anomalies(
        self, series: pd.Series, window: int = 3, threshold: float = 0.2
    ) -> List[Dict[str, Any]]:
        results: list[dict[str, Any]] = []
        if len(series) < window + 1:
            return results

        series = series.dropna()
        ma = series.rolling(window=window).mean().shift(1)

        for i in range(window, len(series)):
            actual = series.iloc[i]
            baseline = ma.iloc[i]

            if pd.isna(baseline) or baseline == 0:
                continue

            deviation = (actual - baseline) / abs(baseline)
            if abs(deviation) >= threshold:
                results.append(
                    {
                        "period": str(series.index[i]),
                        "actual_value": actual,
                        "baseline_value": baseline,
                        "deviation": deviation,
                        "severity": self._get_severity(abs(deviation), threshold),
                        "method": "moving_average",
                    }
                )
        return results

    def _get_severity(self, abs_dev: float, threshold: float) -> str:
        if abs_dev >= threshold * 2:
            return "Critical"
        elif abs_dev >= threshold * 1.5:
            return "High"
        elif abs_dev >= threshold * 1.2:
            return "Medium"
        return "Low"

    def _get_z_severity(self, abs_z: float, threshold: float) -> str:
        if abs_z >= threshold + 2:
            return "Critical"
        elif abs_z >= threshold + 1:
            return "High"
        elif abs_z >= threshold + 0.5:
            return "Medium"
        return "Low"

    def summarize_anomalies(self, metric_name: str, series: pd.Series) -> pd.DataFrame:
        if series.empty:
            return pd.DataFrame(
                columns=[
                    "metric",
                    "period",
                    "actual_value",
                    "baseline_value",
                    "deviation",
                    "severity",
                    "method",
                ]
            )

        anomalies = []
        anomalies.extend(self.detect_percentage_deviation(series))
        anomalies.extend(self.detect_z_score_anomalies(series))
        anomalies.extend(self.detect_moving_average_anomalies(series))

        if not anomalies:
            return pd.DataFrame(
                columns=[
                    "metric",
                    "period",
                    "actual_value",
                    "baseline_value",
                    "deviation",
                    "severity",
                    "method",
                ]
            )

        df = pd.DataFrame(anomalies)
        df.insert(0, "metric", metric_name)
        return df.drop_duplicates(subset=["metric", "period", "method"])
