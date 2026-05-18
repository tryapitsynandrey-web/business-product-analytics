import pandas as pd


class SegmentationEngine:
    def segment_by_revenue(self, df: pd.DataFrame) -> pd.DataFrame:
        df_out = df.copy()
        if "mrr" not in df_out.columns and "total_revenue" not in df_out.columns:
            df_out["revenue_segment"] = "No Revenue"
            return df_out

        col = "mrr" if "mrr" in df_out.columns else "total_revenue"

        def assign(val):
            if pd.isna(val) or val <= 0:
                return "No Revenue"
            elif val > 1000:
                return "Enterprise Value"
            elif val >= 100:
                return "Mid Value"
            return "Low Value"

        df_out["revenue_segment"] = df_out[col].apply(assign)
        return df_out

    def segment_by_usage(self, df: pd.DataFrame) -> pd.DataFrame:
        df_out = df.copy()
        if "total_actions" not in df_out.columns:
            df_out["usage_segment"] = "No Usage"
            return df_out

        def assign(val):
            if pd.isna(val) or val == 0:
                return "No Usage"
            elif val >= 50:
                return "Power User"
            elif val >= 10:
                return "Regular User"
            return "Low Usage"

        df_out["usage_segment"] = df_out["total_actions"].apply(assign)
        return df_out

    def segment_by_risk(self, df: pd.DataFrame) -> pd.DataFrame:
        df_out = df.copy()
        if "churn_risk_score" not in df_out.columns:
            df_out["risk_segment"] = "Unknown Risk"
            return df_out

        def assign(val):
            if pd.isna(val):
                return "Unknown Risk"
            elif val >= 80:
                return "Critical Risk"
            elif val >= 60:
                return "High Risk"
            elif val >= 40:
                return "Medium Risk"
            return "Low Risk"

        df_out["risk_segment"] = df_out["churn_risk_score"].apply(assign)
        return df_out

    def segment_by_nps(self, df: pd.DataFrame) -> pd.DataFrame:
        df_out = df.copy()
        if "latest_nps" not in df_out.columns:
            df_out["nps_segment"] = "No NPS"
            return df_out

        def assign(val):
            if pd.isna(val):
                return "No NPS"
            elif val >= 9:
                return "Promoter"
            elif val >= 7:
                return "Passive"
            return "Detractor"

        df_out["nps_segment"] = df_out["latest_nps"].apply(assign)
        return df_out

    def assign_customer_segments(self, customer_360: pd.DataFrame) -> pd.DataFrame:
        if customer_360.empty:
            df = customer_360.copy()
            for col in ["revenue_segment", "usage_segment", "risk_segment", "nps_segment"]:
                df[col] = pd.Series(dtype=str)
            return df

        df = self.segment_by_revenue(customer_360)
        df = self.segment_by_usage(df)
        df = self.segment_by_risk(df)
        df = self.segment_by_nps(df)
        return df

    def build_segment_summary(self, customer_360: pd.DataFrame) -> pd.DataFrame:
        df = self.assign_customer_segments(customer_360)
        if df.empty:
            return pd.DataFrame(
                columns=["segment_type", "segment_name", "customer_count", "percentage"]
            )

        results = []
        total = len(df)

        for col, stype in [
            ("revenue_segment", "Revenue"),
            ("usage_segment", "Usage"),
            ("risk_segment", "Risk"),
            ("nps_segment", "NPS"),
        ]:
            counts = df[col].value_counts().to_dict()
            for name, count in counts.items():
                results.append(
                    {
                        "segment_type": stype,
                        "segment_name": name,
                        "customer_count": count,
                        "percentage": float(count / total) if total > 0 else 0.0,
                    }
                )

        return pd.DataFrame(results)
