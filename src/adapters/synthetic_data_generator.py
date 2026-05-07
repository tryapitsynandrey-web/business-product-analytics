import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import uuid
from typing import Dict

from utils.paths import SYNTHETIC_DATA_DIR

class SyntheticDataGenerator:
    """Generates realistic synthetic SaaS datasets for analytics."""

    def __init__(self, seed: int = 42, num_customers: int = 1000):
        self.seed = seed
        self.num_customers = num_customers
        np.random.seed(self.seed)
        random.seed(self.seed)
        
        self.segments = ['Enterprise', 'Mid-Market', 'SMB', 'Startup']
        self.segment_probs = [0.05, 0.15, 0.40, 0.40]
        
        self.plans = {
            'Basic': 49.0,
            'Pro': 199.0,
            'Premium': 499.0,
            'Enterprise': 1999.0
        }
        self.plan_names = list(self.plans.keys())
        self.plan_probs = [0.4, 0.3, 0.2, 0.1]
        
        self.channels = ['Organic Search', 'Paid Social', 'Direct', 'Referral', 'Outbound Sales']
        self.countries = ['USA', 'UK', 'Canada', 'Germany', 'Australia']
        
        self.start_date = datetime.now() - timedelta(days=365*2) # 2 years of history
        self.end_date = datetime.now()

    def generate_all(self) -> Dict[str, pd.DataFrame]:
        print("Generating synthetic data...")
        customers = self.generate_customers()
        subscriptions = self.generate_subscriptions(customers)
        transactions = self.generate_transactions(subscriptions)
        product_usage = self.generate_product_usage(customers)
        support_tickets = self.generate_support_tickets(customers)
        nps_scores = self.generate_nps_scores(customers)
        acquisition_channels = self.generate_acquisition_channels()
        targets = self.generate_targets()
        
        # Save to CSV
        customers.to_csv(SYNTHETIC_DATA_DIR / 'customers.csv', index=False)
        subscriptions.to_csv(SYNTHETIC_DATA_DIR / 'subscriptions.csv', index=False)
        transactions.to_csv(SYNTHETIC_DATA_DIR / 'transactions.csv', index=False)
        product_usage.to_csv(SYNTHETIC_DATA_DIR / 'product_usage.csv', index=False)
        support_tickets.to_csv(SYNTHETIC_DATA_DIR / 'support_tickets.csv', index=False)
        nps_scores.to_csv(SYNTHETIC_DATA_DIR / 'nps_scores.csv', index=False)
        acquisition_channels.to_csv(SYNTHETIC_DATA_DIR / 'acquisition_channels.csv', index=False)
        targets.to_csv(SYNTHETIC_DATA_DIR / 'targets.csv', index=False)
        
        return {
            'customers': customers,
            'subscriptions': subscriptions,
            'transactions': transactions,
            'product_usage': product_usage,
            'support_tickets': support_tickets,
            'nps_scores': nps_scores,
            'acquisition_channels': acquisition_channels,
            'targets': targets
        }

    def _random_dates(self, start, end, n):
        start_u = start.value // 10**9
        end_u = end.value // 10**9
        return pd.to_datetime(np.random.randint(start_u, end_u, n), unit='s')

    def generate_customers(self) -> pd.DataFrame:
        customer_ids = [f"CUST-{str(uuid.uuid4())[:8]}" for _ in range(self.num_customers)]
        signups = self._random_dates(pd.Timestamp(self.start_date), pd.Timestamp(self.end_date), self.num_customers)
        
        data = {
            'customer_id': customer_ids,
            'company_name': [f"Company {i}" for i in range(self.num_customers)],
            'segment': np.random.choice(self.segments, self.num_customers, p=self.segment_probs),
            'country': np.random.choice(self.countries, self.num_customers),
            'signup_date': signups,
            'acquisition_channel': np.random.choice(self.channels, self.num_customers),
            'is_active': np.random.choice([True, False], self.num_customers, p=[0.7, 0.3])
        }
        return pd.DataFrame(data)

    def generate_subscriptions(self, customers_df: pd.DataFrame) -> pd.DataFrame:
        subs = []
        for _, row in customers_df.iterrows():
            plan = np.random.choice(self.plan_names, p=self.plan_probs)
            start = row['signup_date']
            status = 'Active' if row['is_active'] else 'Canceled'
            
            # 10% past due for active
            if status == 'Active' and random.random() < 0.1:
                status = 'Past Due'
                
            end_date = None
            if status == 'Canceled':
                days_active = random.randint(30, max(31, (self.end_date - start).days))
                end_date = start + timedelta(days=days_active)
            
            subs.append({
                'subscription_id': f"SUB-{str(uuid.uuid4())[:8]}",
                'customer_id': row['customer_id'],
                'plan': plan,
                'status': status,
                'start_date': start.date(),
                'end_date': end_date.date() if end_date else None,
                'monthly_price': self.plans[plan],
                'billing_cycle': 'Monthly',
                'auto_renew': status in ['Active', 'Past Due']
            })
        return pd.DataFrame(subs)

    def generate_transactions(self, subscriptions_df: pd.DataFrame) -> pd.DataFrame:
        transactions = []
        for _, row in subscriptions_df.iterrows():
            start = pd.Timestamp(row['start_date'])
            end = pd.Timestamp(row['end_date']) if pd.notnull(row['end_date']) else pd.Timestamp(self.end_date)
            
            current_date = start
            while current_date < end:
                status = 'Success'
                # Simulate some failed payments
                if random.random() < 0.05:
                    status = 'Failed'
                elif random.random() < 0.02:
                    status = 'Refunded'
                    
                transactions.append({
                    'transaction_id': f"TXN-{str(uuid.uuid4())[:8]}",
                    'customer_id': row['customer_id'],
                    'subscription_id': row['subscription_id'],
                    'amount': row['monthly_price'],
                    'currency': 'USD',
                    'status': status,
                    'transaction_date': current_date.date(),
                    'payment_method': np.random.choice(['Credit Card', 'Wire Transfer', 'PayPal'])
                })
                current_date += pd.DateOffset(months=1)
                
        return pd.DataFrame(transactions)

    def generate_product_usage(self, customers_df: pd.DataFrame) -> pd.DataFrame:
        usage = []
        for _, row in customers_df.iterrows():
            # generate monthly usage stats
            start = pd.Timestamp(row['signup_date']).replace(day=1)
            end = pd.Timestamp(self.end_date).replace(day=1)
            
            # Active users decline if not active
            base_logins = random.randint(10, 500)
            
            current = start
            while current <= end:
                is_active_month = row['is_active'] or current < pd.Timestamp(self.end_date) - pd.DateOffset(months=3)
                if not is_active_month:
                    logins = random.randint(0, 5)
                else:
                    logins = max(1, int(base_logins * random.uniform(0.8, 1.2)))
                    
                usage.append({
                    'usage_id': f"USG-{str(uuid.uuid4())[:8]}",
                    'customer_id': row['customer_id'],
                    'date': current.date(),
                    'active_users': max(1, logins // 10),
                    'key_actions': max(0, logins * random.randint(1, 5)),
                    'logins': logins,
                    'features_used': random.randint(1, 10)
                })
                current += pd.DateOffset(months=1)
        return pd.DataFrame(usage)

    def generate_support_tickets(self, customers_df: pd.DataFrame) -> pd.DataFrame:
        tickets = []
        for _, row in customers_df.iterrows():
            num_tickets = random.randint(0, 5)
            for _ in range(num_tickets):
                open_date = row['signup_date'] + timedelta(days=random.randint(0, 300))
                if open_date > pd.Timestamp(self.end_date):
                    continue
                    
                tickets.append({
                    'ticket_id': f"TKT-{str(uuid.uuid4())[:8]}",
                    'customer_id': row['customer_id'],
                    'date_opened': open_date.date(),
                    'date_closed': (open_date + timedelta(days=random.randint(1, 10))).date(),
                    'status': 'Closed',
                    'priority': np.random.choice(['Low', 'Medium', 'High', 'Urgent']),
                    'category': np.random.choice(['Billing', 'Technical', 'How-to', 'Bug']),
                    'resolution_time_hours': random.randint(1, 72)
                })
        return pd.DataFrame(tickets)

    def generate_nps_scores(self, customers_df: pd.DataFrame) -> pd.DataFrame:
        nps = []
        for _, row in customers_df.iterrows():
            if random.random() < 0.4: # 40% response rate
                score_date = row['signup_date'] + timedelta(days=random.randint(30, 300))
                if score_date > pd.Timestamp(self.end_date):
                    continue
                score = random.randint(0, 10)
                # inactive customers more likely to give bad scores
                if not row['is_active'] and random.random() < 0.7:
                    score = random.randint(0, 6)
                elif row['is_active'] and random.random() < 0.7:
                    score = random.randint(7, 10)
                    
                nps.append({
                    'score_id': f"NPS-{str(uuid.uuid4())[:8]}",
                    'customer_id': row['customer_id'],
                    'date': score_date.date(),
                    'score': score,
                    'feedback_category': np.random.choice(['Pricing', 'Features', 'Support', 'Reliability'])
                })
        return pd.DataFrame(nps)

    def generate_acquisition_channels(self) -> pd.DataFrame:
        return pd.DataFrame({
            'channel_name': self.channels,
            'cost_per_acquisition': [150.0, 200.0, 0.0, 50.0, 500.0]
        })

    def generate_targets(self) -> pd.DataFrame:
        return pd.DataFrame({
            'metric_name': ['MRR', 'Churn Rate', 'Activation Rate', 'NPS'],
            'target_value': [100000.0, 0.02, 0.85, 40.0],
            'date': [self.end_date.replace(day=1).date()] * 4
        })

if __name__ == "__main__":
    generator = SyntheticDataGenerator()
    generator.generate_all()
