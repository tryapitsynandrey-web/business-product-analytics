import pandas as pd
from typing import Dict, Any


class FunnelAnalysisEngine:
    def calculate_funnel_steps(
        self, customers: pd.DataFrame, product_usage: pd.DataFrame, subscriptions: pd.DataFrame
    ) -> Dict[str, int]:
        if customers.empty:
            return {
                "Signup": 0,
                "Activation": 0,
                "Key Action": 0,
                "Paid Conversion": 0,
                "Month-1 Retention": 0,
            }

        signups = set(customers["customer_id"].unique())

        # Activation
        activated = set()
        if "is_activated" in customers.columns:
            activated.update(customers[customers["is_activated"].eq(True)]["customer_id"].unique())
        if "activation_date" in customers.columns:
            activated.update(
                customers[customers["activation_date"].notnull()]["customer_id"].unique()
            )

        # Key Actions
        key_action_users = set()
        if not product_usage.empty and "key_actions" in product_usage.columns:
            usage_by_customer = product_usage.groupby("customer_id")["key_actions"].sum()
            activated.update(usage_by_customer[usage_by_customer >= 5].index)
            key_action_users = set(usage_by_customer[usage_by_customer > 0].index)

        # Paid Conversion
        paid_users = set()
        if not subscriptions.empty:
            paid = subscriptions[subscriptions["status"].isin(["Active", "Past Due", "Canceled"])]
            if "monthly_price" in paid.columns:
                paid = paid[paid["monthly_price"] > 0]
            paid_users = set(paid["customer_id"].unique())

        # Month-1 Retention
        retained_users = set()
        if not subscriptions.empty and "signup_date" in customers.columns:
            cust_signup = customers[["customer_id", "signup_date"]].copy()
            cust_signup["signup_date"] = pd.to_datetime(cust_signup["signup_date"])
            merged = pd.merge(subscriptions, cust_signup, on="customer_id", how="inner")
            merged["end_date"] = pd.to_datetime(merged["end_date"])

            # Active after 30 days means: end_date is null OR end_date > signup_date + 30 days
            retained = merged[
                merged["end_date"].isnull()
                | (merged["end_date"] > merged["signup_date"] + pd.Timedelta(days=30))
            ]
            retained_users = set(retained["customer_id"].unique())

        return {
            "Signup": len(signups),
            "Activation": len(signups.intersection(activated)),
            "Key Action": len(signups.intersection(activated).intersection(key_action_users)),
            "Paid Conversion": len(
                signups.intersection(activated)
                .intersection(key_action_users)
                .intersection(paid_users)
            ),
            "Month-1 Retention": len(
                signups.intersection(activated)
                .intersection(key_action_users)
                .intersection(paid_users)
                .intersection(retained_users)
            ),
        }

    def calculate_step_conversion(self, funnel_steps: Dict[str, int]) -> pd.DataFrame:
        steps = ["Signup", "Activation", "Key Action", "Paid Conversion", "Month-1 Retention"]

        results = []
        prev_users = None
        for step in steps:
            users = funnel_steps.get(step, 0)
            if prev_users is None:
                conv = 1.0
                drop = 0.0
                prev = users
            else:
                conv = float(users / prev_users) if prev_users > 0 else 0.0
                drop = 1.0 - conv
                prev = prev_users

            results.append(
                {
                    "step": step,
                    "users": users,
                    "conversion_rate": conv,
                    "dropoff_rate": drop,
                    "previous_step_users": prev,
                }
            )
            prev_users = users

        return pd.DataFrame(results)

    def identify_largest_bottleneck(self, funnel_summary: pd.DataFrame) -> Dict[str, Any]:
        if funnel_summary.empty or len(funnel_summary) <= 1:
            return {"step": "None", "dropoff_rate": 0.0}

        # exclude the first step as it has no dropoff
        drops = funnel_summary.iloc[1:]
        max_drop = drops.loc[drops["dropoff_rate"].idxmax()]
        dropoff_rate = max_drop["dropoff_rate"]

        return {
            "step": str(max_drop["step"]),
            "dropoff_rate": float(
                dropoff_rate.iloc[0] if isinstance(dropoff_rate, pd.Series) else dropoff_rate
            ),
        }

    def calculate_segment_funnel(
        self, customers: pd.DataFrame, product_usage: pd.DataFrame, subscriptions: pd.DataFrame
    ) -> pd.DataFrame:
        if customers.empty:
            return pd.DataFrame(
                columns=[
                    "segment",
                    "step",
                    "users",
                    "conversion_rate",
                    "dropoff_rate",
                    "previous_step_users",
                ]
            )

        customers_df = customers.copy()
        if "segment" not in customers_df.columns:
            customers_df["segment"] = "Unknown"

        customers_df["segment"] = customers_df["segment"].fillna("Unknown")

        all_results = []
        for segment, group in customers_df.groupby("segment"):
            group_cust_ids = set(group["customer_id"].unique())

            group_usage = (
                product_usage[product_usage["customer_id"].isin(group_cust_ids)]
                if not product_usage.empty
                else pd.DataFrame()
            )
            group_subs = (
                subscriptions[subscriptions["customer_id"].isin(group_cust_ids)]
                if not subscriptions.empty
                else pd.DataFrame()
            )

            steps = self.calculate_funnel_steps(group, group_usage, group_subs)
            summary = self.calculate_step_conversion(steps)
            summary.insert(0, "segment", segment)
            all_results.append(summary)

        if not all_results:
            return pd.DataFrame(
                columns=[
                    "segment",
                    "step",
                    "users",
                    "conversion_rate",
                    "dropoff_rate",
                    "previous_step_users",
                ]
            )

        return pd.concat(all_results, ignore_index=True)
