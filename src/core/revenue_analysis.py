import pandas as pd
from typing import Dict, Any


class RevenueAnalysisEngine:
    def analyze_revenue_by_month(self, transactions: pd.DataFrame) -> pd.DataFrame:
        if transactions.empty:
            return pd.DataFrame(
                columns=["period", "gross_revenue", "refunds", "failed_payments", "net_revenue"]
            )

        df = transactions.copy()
        df["transaction_date"] = pd.to_datetime(df["transaction_date"])
        df["period"] = df["transaction_date"].dt.to_period("M")

        df["gross_revenue"] = 0.0
        df["refunds"] = 0.0
        df["failed_payments"] = 0.0

        if "status" in df.columns and "amount" in df.columns:
            df.loc[df["status"] == "Success", "gross_revenue"] = df["amount"]
            df.loc[df["status"] == "Refunded", "refunds"] = df["amount"]
            df.loc[df["status"] == "Failed", "failed_payments"] = df["amount"]

        grouped = (
            df.groupby("period")
            .agg({"gross_revenue": "sum", "refunds": "sum", "failed_payments": "sum"})
            .reset_index()
        )

        grouped["net_revenue"] = grouped["gross_revenue"] - grouped["refunds"]
        grouped["period"] = grouped["period"].astype(str)
        return grouped

    def analyze_revenue_by_segment(
        self, transactions: pd.DataFrame, customers: pd.DataFrame
    ) -> pd.DataFrame:
        if transactions.empty or customers.empty:
            return pd.DataFrame(
                columns=["segment", "gross_revenue", "refunds", "failed_payments", "net_revenue"]
            )

        merged = pd.merge(
            transactions, customers[["customer_id", "segment"]], on="customer_id", how="left"
        )
        merged["segment"] = merged["segment"].fillna("Unknown")

        merged["gross_revenue"] = 0.0
        merged["refunds"] = 0.0
        merged["failed_payments"] = 0.0

        if "status" in merged.columns and "amount" in merged.columns:
            merged.loc[merged["status"] == "Success", "gross_revenue"] = merged["amount"]
            merged.loc[merged["status"] == "Refunded", "refunds"] = merged["amount"]
            merged.loc[merged["status"] == "Failed", "failed_payments"] = merged["amount"]

        grouped = (
            merged.groupby("segment")
            .agg({"gross_revenue": "sum", "refunds": "sum", "failed_payments": "sum"})
            .reset_index()
        )

        grouped["net_revenue"] = grouped["gross_revenue"] - grouped["refunds"]
        return grouped

    def analyze_revenue_by_plan(
        self, transactions: pd.DataFrame, subscriptions: pd.DataFrame
    ) -> pd.DataFrame:
        if transactions.empty or subscriptions.empty:
            return pd.DataFrame(
                columns=["plan", "gross_revenue", "refunds", "failed_payments", "net_revenue"]
            )

        merged = pd.merge(
            transactions,
            subscriptions[["subscription_id", "plan"]],
            on="subscription_id",
            how="left",
        )
        merged["plan"] = merged["plan"].fillna("Unknown")

        merged["gross_revenue"] = 0.0
        merged["refunds"] = 0.0
        merged["failed_payments"] = 0.0

        if "status" in merged.columns and "amount" in merged.columns:
            merged.loc[merged["status"] == "Success", "gross_revenue"] = merged["amount"]
            merged.loc[merged["status"] == "Refunded", "refunds"] = merged["amount"]
            merged.loc[merged["status"] == "Failed", "failed_payments"] = merged["amount"]

        grouped = (
            merged.groupby("plan")
            .agg({"gross_revenue": "sum", "refunds": "sum", "failed_payments": "sum"})
            .reset_index()
        )

        grouped["net_revenue"] = grouped["gross_revenue"] - grouped["refunds"]
        return grouped

    def calculate_refund_impact(self, transactions: pd.DataFrame) -> float:
        if transactions.empty or "status" not in transactions.columns:
            return 0.0
        success = transactions.loc[transactions["status"] == "Success", "amount"].sum()
        if success == 0:
            return 0.0
        refunds = transactions.loc[transactions["status"] == "Refunded", "amount"].sum()
        return float(refunds / success)

    def calculate_failed_payment_impact(self, transactions: pd.DataFrame) -> float:
        if transactions.empty or "status" not in transactions.columns:
            return 0.0
        success = transactions.loc[transactions["status"] == "Success", "amount"].sum()
        if success == 0:
            return 0.0
        failed = transactions.loc[transactions["status"] == "Failed", "amount"].sum()
        return float(failed / success)

    def calculate_revenue_movement(self, transactions: pd.DataFrame) -> pd.DataFrame:
        monthly = self.analyze_revenue_by_month(transactions)
        if monthly.empty:
            return pd.DataFrame(
                columns=["period", "net_revenue", "previous_revenue", "revenue_growth_rate"]
            )

        monthly = monthly.sort_values("period").reset_index(drop=True)
        monthly["previous_revenue"] = monthly["net_revenue"].shift(1).fillna(0.0)

        def calc_growth(row):
            if row["previous_revenue"] == 0:
                return 0.0
            return float(
                (row["net_revenue"] - row["previous_revenue"]) / abs(row["previous_revenue"])
            )

        monthly["revenue_growth_rate"] = monthly.apply(calc_growth, axis=1)
        return monthly[["period", "net_revenue", "previous_revenue", "revenue_growth_rate"]]

    def summarize_revenue_health(self, transactions: pd.DataFrame) -> Dict[str, Any]:
        if transactions.empty:
            return {
                "gross_revenue": 0.0,
                "net_revenue": 0.0,
                "refund_rate": 0.0,
                "failed_payment_rate": 0.0,
                "status": "Critical",
            }

        monthly = self.analyze_revenue_by_month(transactions)
        gross = float(monthly["gross_revenue"].sum())
        net = float(monthly["net_revenue"].sum())

        refund_rate = self.calculate_refund_impact(transactions)
        failed_rate = self.calculate_failed_payment_impact(transactions)

        status = "Healthy"
        if refund_rate > 0.1 or failed_rate > 0.15:
            status = "Critical"
        elif refund_rate > 0.05 or failed_rate > 0.08:
            status = "Risk"
        elif refund_rate > 0.02 or failed_rate > 0.03:
            status = "Watch"

        return {
            "gross_revenue": gross,
            "net_revenue": net,
            "refund_rate": refund_rate,
            "failed_payment_rate": failed_rate,
            "status": status,
        }
