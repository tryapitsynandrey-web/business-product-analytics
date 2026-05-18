import pandas as pd
import numpy as np
from datetime import date, datetime, timedelta
import random
import hashlib
from pathlib import Path
from typing import Dict

from utils.paths import SYNTHETIC_DATA_DIR


class SyntheticDataGenerator:
    """Generates realistic synthetic SaaS datasets for analytics."""

    def __init__(
        self,
        seed: int = 42,
        num_customers: int = 1000,
        as_of_date: date | datetime | str | None = None,
        output_dir: Path | None = None,
    ):
        self.seed = seed
        self.num_customers = num_customers
        self.np_rng = np.random.default_rng(self.seed)
        self.py_rng = random.Random(self.seed)
        self.output_dir = output_dir or SYNTHETIC_DATA_DIR

        self.segments = ["Enterprise", "Mid-Market", "SMB", "Startup"]
        self.segment_probs = [0.05, 0.15, 0.40, 0.40]

        self.plans = {"Basic": 49.0, "Pro": 199.0, "Premium": 499.0, "Enterprise": 1999.0}
        self.plan_names = list(self.plans.keys())
        self.plan_probs = [0.4, 0.3, 0.2, 0.1]

        self.channels = ["Organic Search", "Paid Social", "Direct", "Referral", "Outbound Sales"]
        self.countries = ["USA", "UK", "Canada", "Germany", "Australia"]

        if as_of_date is None:
            parsed_as_of = pd.Timestamp("2026-05-01")
        else:
            parsed_as_of = pd.Timestamp(as_of_date)
        self.end_date = parsed_as_of.normalize()
        self.start_date = self.end_date - timedelta(days=365 * 2)  # 2 years of history

    def _stable_id(self, prefix: str, index: int) -> str:
        digest = hashlib.sha1(f"{self.seed}:{prefix}:{index}".encode("utf-8")).hexdigest()
        return f"{prefix}-{digest[:8].upper()}"

    def generate_all(self) -> Dict[str, pd.DataFrame]:
        print("Generating synthetic data...")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        customers = self.generate_customers()
        subscriptions = self.generate_subscriptions(customers)
        transactions = self.generate_transactions(subscriptions)
        product_usage = self.generate_product_usage(customers)
        support_tickets = self.generate_support_tickets(customers)
        nps_scores = self.generate_nps_scores(customers)
        acquisition_channels = self.generate_acquisition_channels()
        targets = self.generate_targets()

        # Save to CSV
        customers.to_csv(self.output_dir / "customers.csv", index=False)
        subscriptions.to_csv(self.output_dir / "subscriptions.csv", index=False)
        transactions.to_csv(self.output_dir / "transactions.csv", index=False)
        product_usage.to_csv(self.output_dir / "product_usage.csv", index=False)
        support_tickets.to_csv(self.output_dir / "support_tickets.csv", index=False)
        nps_scores.to_csv(self.output_dir / "nps_scores.csv", index=False)
        acquisition_channels.to_csv(self.output_dir / "acquisition_channels.csv", index=False)
        targets.to_csv(self.output_dir / "targets.csv", index=False)

        return {
            "customers": customers,
            "subscriptions": subscriptions,
            "transactions": transactions,
            "product_usage": product_usage,
            "support_tickets": support_tickets,
            "nps_scores": nps_scores,
            "acquisition_channels": acquisition_channels,
            "targets": targets,
        }

    def _random_dates(self, start, end, n):
        start_u = start.value // 10**9
        end_u = end.value // 10**9
        return pd.to_datetime(self.np_rng.integers(start_u, end_u, n), unit="s")

    def generate_customers(self) -> pd.DataFrame:
        customer_ids = [self._stable_id("CUST", i) for i in range(self.num_customers)]
        signups = self._random_dates(
            pd.Timestamp(self.start_date), pd.Timestamp(self.end_date), self.num_customers
        )

        data = {
            "customer_id": customer_ids,
            "company_name": [f"Company {i}" for i in range(self.num_customers)],
            "segment": self.np_rng.choice(self.segments, self.num_customers, p=self.segment_probs),
            "country": self.np_rng.choice(self.countries, self.num_customers),
            "signup_date": signups,
            "acquisition_channel": self.np_rng.choice(self.channels, self.num_customers),
            "is_active": self.np_rng.choice([True, False], self.num_customers, p=[0.7, 0.3]),
        }
        return pd.DataFrame(data)

    def generate_subscriptions(self, customers_df: pd.DataFrame) -> pd.DataFrame:
        subs = []
        for i, (_, row) in enumerate(customers_df.iterrows()):
            plan = self.np_rng.choice(self.plan_names, p=self.plan_probs)
            start = row["signup_date"]
            status = "Active" if row["is_active"] else "Canceled"

            # 10% past due for active
            if status == "Active" and self.py_rng.random() < 0.1:
                status = "Past Due"

            end_date = None
            if status == "Canceled":
                max_days_active = max(1, (self.end_date - start).days)
                min_days_active = min(30, max_days_active)
                days_active = self.py_rng.randint(min_days_active, max_days_active)
                end_date = start + timedelta(days=days_active)

            subs.append(
                {
                    "subscription_id": self._stable_id("SUB", i),
                    "customer_id": row["customer_id"],
                    "plan": plan,
                    "status": status,
                    "start_date": start.date(),
                    "end_date": end_date.date() if end_date else None,
                    "monthly_price": self.plans[plan],
                    "billing_cycle": "Monthly",
                    "auto_renew": status in ["Active", "Past Due"],
                }
            )
        return pd.DataFrame(subs)

    def generate_transactions(self, subscriptions_df: pd.DataFrame) -> pd.DataFrame:
        transactions = []
        transaction_idx = 0
        for _, row in subscriptions_df.iterrows():
            start = pd.Timestamp(row["start_date"])
            end = (
                pd.Timestamp(row["end_date"])
                if pd.notnull(row["end_date"])
                else pd.Timestamp(self.end_date)
            )

            current_date = start
            while current_date < end:
                status = "Success"
                # Simulate some failed payments
                if self.py_rng.random() < 0.05:
                    status = "Failed"
                elif self.py_rng.random() < 0.02:
                    status = "Refunded"

                transactions.append(
                    {
                        "transaction_id": self._stable_id("TXN", transaction_idx),
                        "customer_id": row["customer_id"],
                        "subscription_id": row["subscription_id"],
                        "amount": row["monthly_price"],
                        "currency": "USD",
                        "status": status,
                        "transaction_date": current_date.date(),
                        "payment_method": self.np_rng.choice(
                            ["Credit Card", "Wire Transfer", "PayPal"]
                        ),
                    }
                )
                transaction_idx += 1
                current_date += pd.DateOffset(months=1)

        return pd.DataFrame(transactions)

    def generate_product_usage(self, customers_df: pd.DataFrame) -> pd.DataFrame:
        usage = []
        usage_idx = 0
        for _, row in customers_df.iterrows():
            # generate monthly usage stats
            start = pd.Timestamp(row["signup_date"]).replace(day=1)
            end = pd.Timestamp(self.end_date).replace(day=1)

            # Active users decline if not active
            base_logins = self.py_rng.randint(10, 500)

            current = start
            while current <= end:
                is_active_month = row["is_active"] or current < pd.Timestamp(
                    self.end_date
                ) - pd.DateOffset(months=3)
                if not is_active_month:
                    logins = self.py_rng.randint(0, 5)
                else:
                    logins = max(1, int(base_logins * self.py_rng.uniform(0.8, 1.2)))

                usage.append(
                    {
                        "usage_id": self._stable_id("USG", usage_idx),
                        "customer_id": row["customer_id"],
                        "date": current.date(),
                        "active_users": max(1, logins // 10),
                        "key_actions": max(0, logins * self.py_rng.randint(1, 5)),
                        "logins": logins,
                        "features_used": self.py_rng.randint(1, 10),
                    }
                )
                usage_idx += 1
                current += pd.DateOffset(months=1)
        return pd.DataFrame(usage)

    def generate_support_tickets(self, customers_df: pd.DataFrame) -> pd.DataFrame:
        tickets = []
        ticket_idx = 0
        for _, row in customers_df.iterrows():
            num_tickets = self.py_rng.randint(0, 5)
            for _ in range(num_tickets):
                open_date = row["signup_date"] + timedelta(days=self.py_rng.randint(0, 300))
                if open_date > pd.Timestamp(self.end_date):
                    continue

                tickets.append(
                    {
                        "ticket_id": self._stable_id("TKT", ticket_idx),
                        "customer_id": row["customer_id"],
                        "date_opened": open_date.date(),
                        "date_closed": (
                            open_date + timedelta(days=self.py_rng.randint(1, 10))
                        ).date(),
                        "status": "Closed",
                        "priority": self.np_rng.choice(["Low", "Medium", "High", "Urgent"]),
                        "category": self.np_rng.choice(["Billing", "Technical", "How-to", "Bug"]),
                        "resolution_time_hours": self.py_rng.randint(1, 72),
                    }
                )
                ticket_idx += 1
        return pd.DataFrame(tickets)

    def generate_nps_scores(self, customers_df: pd.DataFrame) -> pd.DataFrame:
        nps = []
        nps_idx = 0
        for _, row in customers_df.iterrows():
            if self.py_rng.random() < 0.4:  # 40% response rate
                score_date = row["signup_date"] + timedelta(days=self.py_rng.randint(30, 300))
                if score_date > pd.Timestamp(self.end_date):
                    continue
                score = self.py_rng.randint(0, 10)
                # inactive customers more likely to give bad scores
                if not row["is_active"] and self.py_rng.random() < 0.7:
                    score = self.py_rng.randint(0, 6)
                elif row["is_active"] and self.py_rng.random() < 0.7:
                    score = self.py_rng.randint(7, 10)

                nps.append(
                    {
                        "score_id": self._stable_id("NPS", nps_idx),
                        "customer_id": row["customer_id"],
                        "date": score_date.date(),
                        "score": score,
                        "feedback_category": self.np_rng.choice(
                            ["Pricing", "Features", "Support", "Reliability"]
                        ),
                    }
                )
                nps_idx += 1
        return pd.DataFrame(nps)

    def generate_acquisition_channels(self) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "channel_name": self.channels,
                "cost_per_acquisition": [150.0, 200.0, 0.0, 50.0, 500.0],
            }
        )

    def generate_targets(self) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "metric_name": ["MRR", "Churn Rate", "Activation Rate", "NPS"],
                "target_value": [100000.0, 0.02, 0.85, 40.0],
                "date": [self.end_date.replace(day=1).date()] * 4,
            }
        )


if __name__ == "__main__":
    generator = SyntheticDataGenerator()
    generator.generate_all()
