import pandas as pd
import pytest
from app.ui_helpers_actions import (
    prepare_top_actions,
    build_top_actions_overview,
    prepare_action_priority_queue,
    build_decision_brief,
    decision_brief_to_markdown,
    prepare_owner_workload_summary,
)


def test_prepare_top_actions_sorts_by_priority_score():
    df = pd.DataFrame(
        [
            {
                "intervention_id": "IV-2",
                "recommendation_title": "B",
                "priority_score": 10,
                "priority_band": "Low",
            },
            {
                "intervention_id": "IV-1",
                "recommendation_title": "A",
                "priority_score": 50,
                "priority_band": "High",
            },
        ]
    )

    actions = prepare_top_actions(df, limit=1)

    assert len(actions) == 1
    assert actions.iloc[0]["intervention_id"] == "IV-1"


def test_prepare_top_actions_handles_empty_and_missing_score():
    assert prepare_top_actions(None).empty
    df = pd.DataFrame(
        [
            {"intervention_id": "IV-1", "recommendation_title": "A"},
            {"intervention_id": "IV-2", "recommendation_title": "B"},
        ]
    )

    actions = prepare_top_actions(df)

    assert actions["intervention_id"].tolist() == ["IV-1", "IV-2"]


def test_build_top_actions_overview_summarizes_current_queue():
    df = pd.DataFrame(
        [
            {
                "intervention_id": "IV-1",
                "priority_band": "Critical",
                "estimated_revenue_impact": 1000,
                "priority_score": 90,
                "effort_level": "Low",
                "suggested_owner": "Customer Success",
            },
            {
                "intervention_id": "IV-2",
                "priority_band": "High",
                "estimated_revenue_impact": 500,
                "priority_score": 60,
                "effort_level": "Medium",
                "suggested_owner": "Customer Success",
            },
            {
                "intervention_id": "IV-3",
                "priority_band": "Low",
                "estimated_revenue_impact": 100,
                "priority_score": 15,
                "effort_level": "Low",
                "suggested_owner": "Product",
            },
        ]
    )

    overview = build_top_actions_overview(df)

    assert overview["actions"] == 3
    assert overview["critical_high"] == 2
    assert overview["quick_wins"] == 2
    assert overview["owners"] == 2
    assert overview["impact_total"] == 1600.0
    assert overview["average_priority_score"] == pytest.approx(55.0)
    assert overview["top_owner"] == "Customer Success"


def test_build_top_actions_overview_handles_empty_and_unassigned_owner():
    assert build_top_actions_overview(None)["actions"] == 0

    overview = build_top_actions_overview(
        pd.DataFrame(
            [
                {"intervention_id": "IV-1", "priority_band": "Low", "suggested_owner": None},
                {"intervention_id": "IV-2", "priority_band": "Medium"},
            ]
        )
    )

    assert overview["critical_high"] == 0
    assert overview["owners"] == 0
    assert overview["top_owner"] == "Unassigned"


def test_prepare_action_priority_queue_sorts_by_score_impact_and_effort():
    df = pd.DataFrame(
        [
            {
                "intervention_id": "IV-2",
                "recommendation_title": "B",
                "priority_score": 80,
                "estimated_revenue_impact": 500,
                "effort_level": "Medium",
            },
            {
                "intervention_id": "IV-1",
                "recommendation_title": "A",
                "priority_score": 80,
                "estimated_revenue_impact": 500,
                "effort_level": "Low",
            },
            {
                "intervention_id": "IV-3",
                "recommendation_title": "C",
                "priority_score": 70,
                "estimated_revenue_impact": 1000,
                "effort_level": "Low",
            },
        ]
    )

    queue = prepare_action_priority_queue(df, limit=2)

    assert queue["intervention_id"].tolist() == ["IV-1", "IV-2"]
    assert queue.columns.tolist() == [
        "intervention_id",
        "recommendation_title",
        "estimated_revenue_impact",
        "priority_score",
        "effort_level",
    ]


def test_prepare_action_priority_queue_handles_empty_and_missing_id():
    assert prepare_action_priority_queue(None).empty

    queue = prepare_action_priority_queue(pd.DataFrame([{"priority_score": 10}]))

    assert queue["intervention_id"].tolist() == [""]
    assert queue["priority_score"].tolist() == [10]


def test_build_decision_brief_summarizes_intervention_view():
    df = pd.DataFrame(
        [
            {
                "intervention_id": "IV-1",
                "recommendation_title": "Executive save motion",
                "expected_action": "Schedule executive review.",
                "priority_band": "High",
                "estimated_revenue_impact": 1000.0,
                "priority_score": 90.0,
                "suggested_owner": "Customer Success",
            },
            {
                "intervention_id": "IV-2",
                "recommendation_title": "Monitor usage",
                "expected_action": "Track product activity.",
                "priority_band": "Low",
                "estimated_revenue_impact": 500.0,
                "priority_score": 10.0,
                "suggested_owner": "Product",
            },
        ]
    )

    brief = build_decision_brief(df, "Top Actions", "High Priority")

    assert brief["records"] == 2
    assert brief["impact_label"] == "Estimated Revenue Impact"
    assert brief["formatted_impact"] == "$1,500.00"
    assert brief["urgent_count"] == 1
    assert brief["top_actions"][0]["title"] == "Executive save motion"
    assert brief["top_actions"][0]["owner"] == "Customer Success"


def test_build_decision_brief_handles_customer_risk_view():
    df = pd.DataFrame(
        [
            {
                "customer_id": "C-001",
                "segment": "Enterprise",
                "churn_risk_band": "Critical",
                "revenue_at_risk": 400.0,
                "churn_risk_score": 0.95,
                "recommended_action": "Run retention call.",
            },
            {
                "customer_id": "C-002",
                "segment": "SMB",
                "churn_risk_band": "Low",
                "revenue_at_risk": 0.0,
                "churn_risk_score": 0.1,
                "recommended_action": "Monitor.",
            },
        ]
    )

    brief = build_decision_brief(df, "Customer 360", "Retention Focus")

    assert brief["records"] == 2
    assert brief["impact_label"] == "Revenue at Risk"
    assert brief["formatted_impact"] == "$400.00"
    assert brief["urgent_count"] == 1
    assert brief["top_actions"][0]["title"] == "C-001"
    assert brief["top_actions"][0]["action"] == "Run retention call."


def test_decision_brief_empty_and_markdown_export():
    brief = build_decision_brief(pd.DataFrame(), "Recommendations", "Revenue Risk")
    markdown = decision_brief_to_markdown(brief)

    assert brief["records"] == 0
    assert brief["top_actions"] == []
    assert "No rows match current decision view." in brief["summary"]
    assert "# Recommendations" in markdown
    assert "- Quick view: Revenue Risk" in markdown


def test_decision_brief_why_it_matters_variants_and_markdown_skip():
    impact_only = build_decision_brief(
        pd.DataFrame([{"recommendation_title": "A", "estimated_revenue_impact": 10}]),
        "Impact",
    )
    urgent_only = build_decision_brief(
        pd.DataFrame([{"recommendation_title": "B", "priority_band": "High"}]),
        "Urgent",
    )
    neutral = build_decision_brief(pd.DataFrame([{"recommendation_title": "C"}]), "Neutral")

    markdown = decision_brief_to_markdown(
        {
            "title": "Mixed",
            "quick_view": "All",
            "records": 1,
            "impact_label": "Impact",
            "formatted_impact": "$0.00",
            "urgent_count": 0,
            "summary": "Summary",
            "why_it_matters": "Why",
            "top_actions": ["bad-item", {"title": "Good", "action": "Act"}],
        }
    )

    assert "protect or capture" in impact_only["why_it_matters"]
    assert "clear urgent operational risk" in urgent_only["why_it_matters"]
    assert "assign owners" in neutral["why_it_matters"]
    assert "Good" in markdown
    assert "bad-item" not in markdown


def test_decision_brief_falls_back_for_blank_values_and_zero_sort_score():
    brief = build_decision_brief(
        pd.DataFrame(
            [
                {
                    "recommendation_title": "nan",
                    "recommended_action": "   ",
                    "suggested_owner": "none",
                    "priority_band": "<NA>",
                    "priority_score": 0,
                }
            ]
        ),
        "Fallbacks",
    )

    action = brief["top_actions"][0]
    assert action["title"] == "Record"
    assert action["action"] == "Review record details."
    assert action["owner"] == "Unassigned"
    assert action["status"] == "Unscored"


def test_prepare_owner_workload_summary_groups_and_sorts():
    df = pd.DataFrame(
        [
            {
                "suggested_owner": "Sales",
                "priority_band": "High",
                "estimated_revenue_impact": 100.0,
            },
            {
                "suggested_owner": "Success",
                "priority_band": "Critical",
                "estimated_revenue_impact": 300.0,
            },
            {
                "suggested_owner": "Sales",
                "priority_band": "Low",
                "estimated_revenue_impact": 50.0,
            },
        ]
    )

    summary = prepare_owner_workload_summary(df)

    assert summary["owner"].tolist() == ["Success", "Sales"]
    assert summary["records"].tolist() == [1, 2]
    assert summary["critical_high"].tolist() == [1, 1]
    assert summary["impact_total"].tolist() == [300.0, 150.0]


def test_prepare_owner_workload_summary_handles_missing_owner():
    assert prepare_owner_workload_summary(None).empty
    assert prepare_owner_workload_summary(pd.DataFrame()).empty
    assert prepare_owner_workload_summary(pd.DataFrame({"priority_band": ["High"]})).empty
