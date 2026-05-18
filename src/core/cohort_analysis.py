from typing import Any

import pandas as pd


class CohortAnalysisEngine:
    def __init__(self, as_of_date: Any | None = None) -> None:
        self.as_of_date = (
            pd.Timestamp(as_of_date).normalize()
            if as_of_date is not None
            else pd.Timestamp.today().normalize()
        )

    def build_signup_cohorts(self, customers: pd.DataFrame) -> pd.DataFrame:
        if customers.empty or "signup_date" not in customers.columns:
            return pd.DataFrame(columns=["customer_id", "cohort_month"])
        df = customers[["customer_id", "signup_date"]].copy()
        df["signup_date"] = pd.to_datetime(df["signup_date"])
        df["cohort_month"] = df["signup_date"].dt.to_period("M").astype(str)
        return df[["customer_id", "cohort_month"]]

    def calculate_cohort_retention(
        self, customers: pd.DataFrame, subscriptions: pd.DataFrame
    ) -> pd.DataFrame:
        if customers.empty or subscriptions.empty:
            return pd.DataFrame(
                columns=[
                    "cohort_month",
                    "period_number",
                    "customers_in_cohort",
                    "retained_customers",
                    "retention_rate",
                ]
            )

        cohorts = self.build_signup_cohorts(customers)
        df = pd.merge(subscriptions, cohorts, on="customer_id", how="inner")
        df["start_date"] = pd.to_datetime(df["start_date"])
        df["end_date"] = pd.to_datetime(df["end_date"])

        # Max date to calculate periods
        max_date = df["start_date"].max() if df["end_date"].isnull().all() else self.as_of_date

        results = []
        for cohort, group in df.groupby("cohort_month"):
            cohort_str = str(cohort)
            cohort_size = int(group["customer_id"].nunique())

            # evaluate up to 12 periods or current date
            for period in range(13):
                eval_period = pd.Period(cohort_str, freq="M") + period
                eval_date = eval_period.end_time

                # Check if this period is entirely in the future
                if eval_period.start_time > max_date:
                    break

                # retained if start <= eval_date and (end is null or end >= eval_date)
                retained = group[
                    (group["start_date"] <= eval_date)
                    & ((group["end_date"].isnull()) | (group["end_date"] >= eval_date))
                ]
                retained_count = int(retained["customer_id"].nunique())

                results.append(
                    {
                        "cohort_month": cohort_str,
                        "period_number": period,
                        "customers_in_cohort": cohort_size,
                        "retained_customers": retained_count,
                        "retention_rate": float(retained_count / cohort_size)
                        if cohort_size > 0
                        else 0.0,
                    }
                )

        return pd.DataFrame(results)

    def calculate_cohort_revenue(
        self, customers: pd.DataFrame, transactions: pd.DataFrame
    ) -> pd.DataFrame:
        if customers.empty or transactions.empty:
            return pd.DataFrame(
                columns=["cohort_month", "period_number", "revenue", "revenue_per_customer"]
            )

        cohorts = self.build_signup_cohorts(customers)
        df = pd.merge(transactions, cohorts, on="customer_id", how="inner")
        df["transaction_date"] = pd.to_datetime(df["transaction_date"])
        df["transaction_month"] = df["transaction_date"].dt.to_period("M")

        # Calculate period_number
        def get_period(row):
            diff = (
                row["transaction_month"].year - pd.Period(row["cohort_month"], freq="M").year
            ) * 12 + (
                row["transaction_month"].month - pd.Period(row["cohort_month"], freq="M").month
            )
            return max(0, diff)

        df["period_number"] = df.apply(get_period, axis=1)

        # Only success
        df["revenue"] = 0.0
        if "status" in df.columns:
            df.loc[df["status"] == "Success", "revenue"] = df["amount"]
        else:
            df["revenue"] = df["amount"]

        grouped = df.groupby(["cohort_month", "period_number"])["revenue"].sum().reset_index()

        # Merge cohort sizes
        cohort_sizes = (
            cohorts.groupby("cohort_month")["customer_id"]
            .nunique()
            .reset_index(name="customers_in_cohort")
        )
        res = pd.merge(grouped, cohort_sizes, on="cohort_month", how="left")

        res["revenue_per_customer"] = res["revenue"] / res["customers_in_cohort"]
        res["revenue_per_customer"] = res["revenue_per_customer"].fillna(0.0)

        return res[["cohort_month", "period_number", "revenue", "revenue_per_customer"]]

    def build_cohort_summary(
        self, customers: pd.DataFrame, subscriptions: pd.DataFrame, transactions: pd.DataFrame
    ) -> pd.DataFrame:
        if customers.empty:
            return pd.DataFrame(
                columns=[
                    "cohort_month",
                    "period_number",
                    "customers_in_cohort",
                    "retained_customers",
                    "retention_rate",
                    "revenue",
                    "revenue_per_customer",
                ]
            )

        retention = self.calculate_cohort_retention(customers, subscriptions)
        revenue = self.calculate_cohort_revenue(customers, transactions)

        if retention.empty and revenue.empty:
            return pd.DataFrame(
                columns=[
                    "cohort_month",
                    "period_number",
                    "customers_in_cohort",
                    "retained_customers",
                    "retention_rate",
                    "revenue",
                    "revenue_per_customer",
                ]
            )
        elif retention.empty:
            revenue["customers_in_cohort"] = 0
            revenue["retained_customers"] = 0
            revenue["retention_rate"] = 0.0
            return revenue
        elif revenue.empty:
            retention["revenue"] = 0.0
            retention["revenue_per_customer"] = 0.0
            return retention

        summary = pd.merge(retention, revenue, on=["cohort_month", "period_number"], how="outer")

        summary["customers_in_cohort"] = summary["customers_in_cohort"].fillna(
            summary.groupby("cohort_month")["customers_in_cohort"].transform("max")
        )
        summary["customers_in_cohort"] = summary["customers_in_cohort"].fillna(0)
        summary["retained_customers"] = summary["retained_customers"].fillna(0)
        summary["retention_rate"] = summary["retention_rate"].fillna(0.0)
        summary["revenue"] = summary["revenue"].fillna(0.0)
        summary["revenue_per_customer"] = summary["revenue_per_customer"].fillna(0.0)

        return summary
