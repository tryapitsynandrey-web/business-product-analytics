from __future__ import annotations

import pandas as pd

from models.pipeline_results import AnalyticsResult, DecisionLayerResult


def test_analytics_result_exposes_mapping_compatibility():
    result = AnalyticsResult(kpis=["kpi"], risk_profiles=["risk"])

    assert result.as_dict()["kpis"] == ["kpi"]
    assert result.get("risk_profiles") == ["risk"]
    assert result.get("missing", "fallback") == "fallback"
    assert result["recommendations"] == []


def test_decision_layer_result_exposes_mapping_compatibility():
    customer_360 = pd.DataFrame({"customer_id": ["C001"]})
    result = DecisionLayerResult(customer_360=customer_360, interventions=[{"id": "I001"}])

    assert result.as_dict()["customer_360"].equals(customer_360)
    assert result.get("interventions") == [{"id": "I001"}]
    assert result.get("missing", "fallback") == "fallback"
    assert result["health_scores"].empty
