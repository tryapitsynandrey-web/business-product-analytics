import pandas as pd
from typing import Dict, Any

class ChurnAnalysisEngine:
    def analyze_churn_by_month(self, subscriptions: pd.DataFrame) -> pd.DataFrame:
        if subscriptions.empty:
            return pd.DataFrame(columns=['period', 'active_customers', 'churned_customers', 'churn_rate', 'retention_rate'])
            
        df = subscriptions.copy()
        df['start_date'] = pd.to_datetime(df['start_date'])
        df['end_date'] = pd.to_datetime(df['end_date'])
        
        min_date = df['start_date'].min()
        max_date = df['start_date'].max() if df['end_date'].isnull().all() else pd.to_datetime('today')
        
        if pd.isna(min_date):
            return pd.DataFrame(columns=['period', 'active_customers', 'churned_customers', 'churn_rate', 'retention_rate'])

        periods = pd.period_range(start=min_date, end=max_date, freq='M')
        
        results = []
        for p in periods:
            p_start = p.start_time
            p_end = p.end_time
            
            # Active: started before or during period, and (no end date OR end date after period start)
            active = df[(df['start_date'] <= p_end) & 
                        ((df['end_date'].isnull()) | (df['end_date'] > p_start))]
            
            # Churned: end_date within this period
            churned = df[(df['end_date'] >= p_start) & (df['end_date'] <= p_end)]
            
            active_count = int(active['customer_id'].nunique())
            churned_count = int(churned['customer_id'].nunique())
            
            churn_rate = self.calculate_churn_rate(active_count, churned_count)
            retention_rate = self.calculate_retention_rate(active_count, churned_count)
            
            results.append({
                'period': str(p),
                'active_customers': active_count,
                'churned_customers': churned_count,
                'churn_rate': churn_rate,
                'retention_rate': retention_rate
            })
            
        return pd.DataFrame(results)

    def analyze_churn_by_segment(self, subscriptions: pd.DataFrame, customers: pd.DataFrame) -> pd.DataFrame:
        if subscriptions.empty or customers.empty:
            return pd.DataFrame(columns=['segment', 'active_customers', 'churned_customers', 'churn_rate', 'retention_rate'])
            
        merged = pd.merge(subscriptions, customers[['customer_id', 'segment']], on='customer_id', how='left')
        merged['segment'] = merged['segment'].fillna('Unknown')
        
        active = merged[merged['status'].isin(['Active', 'Past Due'])]
        churned = merged[merged['status'] == 'Canceled']
        
        active_counts = active.groupby('segment')['customer_id'].nunique().rename('active_customers')
        churned_counts = churned.groupby('segment')['customer_id'].nunique().rename('churned_customers')
        
        df = pd.concat([active_counts, churned_counts], axis=1).fillna(0).reset_index()
        
        df['churn_rate'] = df.apply(lambda x: self.calculate_churn_rate(x['active_customers'], x['churned_customers']), axis=1)
        df['retention_rate'] = df.apply(lambda x: self.calculate_retention_rate(x['active_customers'], x['churned_customers']), axis=1)
        
        return df

    def analyze_churn_by_plan(self, subscriptions: pd.DataFrame) -> pd.DataFrame:
        if subscriptions.empty:
            return pd.DataFrame(columns=['plan', 'active_customers', 'churned_customers', 'churn_rate', 'retention_rate'])
            
        df = subscriptions.copy()
        df['plan'] = df['plan'].fillna('Unknown')
        
        active = df[df['status'].isin(['Active', 'Past Due'])]
        churned = df[df['status'] == 'Canceled']
        
        active_counts = active.groupby('plan')['customer_id'].nunique().rename('active_customers')
        churned_counts = churned.groupby('plan')['customer_id'].nunique().rename('churned_customers')
        
        res = pd.concat([active_counts, churned_counts], axis=1).fillna(0).reset_index()
        
        res['churn_rate'] = res.apply(lambda x: self.calculate_churn_rate(x['active_customers'], x['churned_customers']), axis=1)
        res['retention_rate'] = res.apply(lambda x: self.calculate_retention_rate(x['active_customers'], x['churned_customers']), axis=1)
        
        return res

    def calculate_churn_rate(self, active_customers: int, churned_customers: int) -> float:
        total = active_customers + churned_customers
        if total == 0:
            return 0.0
        return float(churned_customers / total)

    def calculate_retention_rate(self, active_customers: int, churned_customers: int) -> float:
        total = active_customers + churned_customers
        if total == 0:
            return 0.0
        return float(active_customers / total)

    def summarize_churn_health(self, subscriptions: pd.DataFrame) -> Dict[str, Any]:
        if subscriptions.empty:
            return {
                'active_customers': 0,
                'churned_customers': 0,
                'churn_rate': 0.0,
                'retention_rate': 0.0,
                'status': 'Critical'
            }
            
        active = subscriptions[subscriptions['status'].isin(['Active', 'Past Due'])]
        churned = subscriptions[subscriptions['status'] == 'Canceled']
        
        active_count = active['customer_id'].nunique()
        churned_count = churned['customer_id'].nunique()
        
        churn_rate = self.calculate_churn_rate(active_count, churned_count)
        retention_rate = self.calculate_retention_rate(active_count, churned_count)
        
        status = 'Healthy'
        if churn_rate > 0.10:
            status = 'Critical'
        elif churn_rate > 0.07:
            status = 'Risk'
        elif churn_rate > 0.04:
            status = 'Watch'
            
        return {
            'active_customers': active_count,
            'churned_customers': churned_count,
            'churn_rate': churn_rate,
            'retention_rate': retention_rate,
            'status': status
        }
