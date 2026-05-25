import pandas as pd
from typing import Any

from app.ui_helpers_format import (
    ACTION_QUEUE_COLUMNS,
    ACTION_EFFORT_ORDER,
    DECISION_BRIEF_IMPACT_COLUMNS,
    DECISION_BRIEF_IMPACT_LABELS,
    DECISION_BRIEF_TITLE_COLUMNS,
    DECISION_BRIEF_ACTION_COLUMNS,
    DECISION_BRIEF_OWNER_COLUMNS,
    DECISION_BRIEF_STATUS_COLUMNS,
    DECISION_BRIEF_SORT_COLUMNS,
    format_currency,
)


def prepare_top_actions(
    interventions: pd.DataFrame | None,
    limit: int = 10,
) -> pd.DataFrame:
    """Return top interventions ordered by priority score."""
    if interventions is None or interventions.empty:
        return pd.DataFrame()

    df = interventions.copy()
    if "priority_score" in df.columns:
        df["priority_score"] = pd.to_numeric(df["priority_score"], errors="coerce").fillna(0)
        df = df.sort_values("priority_score", ascending=False)

    display_cols = [
        "intervention_id",
        "recommendation_title",
        "priority_band",
        "estimated_revenue_impact",
        "priority_score",
        "effort_level",
        "suggested_owner",
        "target_segment",
    ]
    cols = [col for col in display_cols if col in df.columns]
    return df[cols].head(limit).reset_index(drop=True)


def build_top_actions_overview(actions: pd.DataFrame | None) -> dict[str, Any]:
    """Return high-signal summary metrics for the current action queue."""
    if actions is None or actions.empty:
        return {
            "actions": 0,
            "critical_high": 0,
            "quick_wins": 0,
            "owners": 0,
            "impact_total": 0.0,
            "average_priority_score": 0.0,
            "top_owner": "Unassigned",
        }

    data = actions.copy()
    priority = data.get("priority_band", pd.Series("", index=data.index))
    effort = data.get("effort_level", pd.Series("", index=data.index))
    owner = data.get("suggested_owner", pd.Series("", index=data.index))
    impact = pd.to_numeric(
        data.get("estimated_revenue_impact", pd.Series(0.0, index=data.index)),
        errors="coerce",
    ).fillna(0.0)
    priority_score = pd.to_numeric(
        data.get("priority_score", pd.Series(0.0, index=data.index)),
        errors="coerce",
    ).fillna(0.0)

    priority_normalized = priority.astype(str).str.strip().str.lower()
    effort_normalized = effort.astype(str).str.strip().str.lower()
    owner_clean = owner.apply(lambda value: _clean_display_value(value, "Unassigned"))
    assigned_owners = owner_clean[owner_clean != "Unassigned"]

    top_owner = "Unassigned"
    if not assigned_owners.empty:
        top_owner = str(assigned_owners.value_counts().idxmax())

    return {
        "actions": int(len(data)),
        "critical_high": int(priority_normalized.isin({"critical", "high"}).sum()),
        "quick_wins": int(effort_normalized.eq("low").sum()),
        "owners": int(assigned_owners.nunique()),
        "impact_total": float(impact.sum()),
        "average_priority_score": float(priority_score.mean()),
        "top_owner": top_owner,
    }


def prepare_action_priority_queue(
    actions: pd.DataFrame | None,
    limit: int = 25,
) -> pd.DataFrame:
    """Return a compact action queue sorted by priority, impact, and effort."""
    if actions is None or actions.empty:
        return pd.DataFrame(columns=ACTION_QUEUE_COLUMNS)

    data = actions.copy()
    priority_score = pd.to_numeric(
        data.get("priority_score", pd.Series(0.0, index=data.index)),
        errors="coerce",
    ).fillna(0.0)
    impact = pd.to_numeric(
        data.get("estimated_revenue_impact", pd.Series(0.0, index=data.index)),
        errors="coerce",
    ).fillna(0.0)
    effort = data.get("effort_level", pd.Series("", index=data.index))
    effort_order = effort.astype(str).str.strip().str.lower().map(ACTION_EFFORT_ORDER).fillna(9)

    data["_priority_score"] = priority_score
    data["_estimated_revenue_impact"] = impact
    data["_effort_order"] = effort_order
    data["intervention_id"] = data.get("intervention_id", pd.Series("", index=data.index)).astype(
        str
    )
    display_cols = [col for col in ACTION_QUEUE_COLUMNS if col in data.columns]
    return (
        data.sort_values(
            ["_priority_score", "_estimated_revenue_impact", "_effort_order", "intervention_id"],
            ascending=[False, False, True, True],
        )[display_cols]
        .head(limit)
        .reset_index(drop=True)
    )


def _first_existing_column(df: pd.DataFrame, columns: list[str]) -> str | None:
    for col in columns:
        if col in df.columns:
            return col
    return None


def _clean_display_value(value: object, fallback: str = "Unknown") -> str:
    if value is None:
        return fallback

    text = str(value).strip()
    if not text or text.lower() in {"nan", "nat", "<na>", "none"}:
        return fallback
    return text


def _sum_first_existing_numeric(
    df: pd.DataFrame,
    columns: list[str],
) -> tuple[str | None, float]:
    for col in columns:
        if col in df.columns:
            values = pd.to_numeric(df[col], errors="coerce").fillna(0)
            return col, float(values.sum())
    return None, 0.0


def _row_first_existing_numeric(row: pd.Series, columns: list[str]) -> tuple[str | None, float]:
    for col in columns:
        if col not in row.index:
            continue
        value = pd.to_numeric(pd.Series([row[col]]), errors="coerce").fillna(0).iloc[0]
        return col, float(value)
    return None, 0.0


def _count_urgent_records(df: pd.DataFrame) -> int:
    return int(_urgent_record_mask(df).sum())


def _urgent_record_mask(df: pd.DataFrame) -> pd.Series:
    available = [col for col in DECISION_BRIEF_STATUS_COLUMNS if col in df.columns]
    mask = pd.Series(False, index=df.index)
    if not available:
        return mask

    urgent_values = {"critical", "high"}
    for col in available:
        values = df[col].astype(str).str.strip().str.lower()
        mask = mask | values.isin(urgent_values)
    return mask


def _sort_decision_brief_rows(df: pd.DataFrame) -> pd.DataFrame:
    available = [col for col in DECISION_BRIEF_SORT_COLUMNS if col in df.columns]
    if not available:
        return df

    score = pd.Series(0.0, index=df.index)
    for col in available:
        values = pd.to_numeric(df[col], errors="coerce").fillna(0)
        score = score.where(score >= values, values)

    if not bool(score.gt(0).any()):
        return df

    sortable = df.copy()
    sortable["_decision_brief_sort_score"] = score
    return sortable.sort_values("_decision_brief_sort_score", ascending=False).drop(
        columns=["_decision_brief_sort_score"]
    )


def _build_decision_brief_actions(df: pd.DataFrame, max_items: int) -> list[dict[str, str]]:
    title_col = _first_existing_column(df, DECISION_BRIEF_TITLE_COLUMNS)
    action_col = _first_existing_column(df, DECISION_BRIEF_ACTION_COLUMNS)
    owner_col = _first_existing_column(df, DECISION_BRIEF_OWNER_COLUMNS)
    status_col = _first_existing_column(df, DECISION_BRIEF_STATUS_COLUMNS)

    actions = []
    for _, row in _sort_decision_brief_rows(df).head(max_items).iterrows():
        impact_col, impact_value = _row_first_existing_numeric(row, DECISION_BRIEF_IMPACT_COLUMNS)
        impact_label = DECISION_BRIEF_IMPACT_LABELS.get(impact_col or "", "Impact")

        title = _clean_display_value(row.get(title_col), "Record") if title_col else "Record"
        action = (
            _clean_display_value(row.get(action_col), "Review record details.")
            if action_col
            else "Review record details."
        )
        owner = (
            _clean_display_value(row.get(owner_col), "Unassigned") if owner_col else "Unassigned"
        )
        status = _clean_display_value(row.get(status_col), "Unscored") if status_col else "Unscored"

        actions.append(
            {
                "title": title,
                "action": action,
                "owner": owner,
                "status": status,
                "impact_label": impact_label,
                "impact": format_currency(impact_value),
            }
        )

    return actions


def build_decision_brief(
    df: pd.DataFrame | None,
    title: str,
    quick_view: str = "All",
    max_items: int = 3,
) -> dict[str, Any]:
    """Return a display-ready decision brief for the current dashboard view."""
    if df is None or df.empty:
        return {
            "title": title,
            "quick_view": quick_view,
            "records": 0,
            "impact_label": "Revenue Impact",
            "impact_total": 0.0,
            "formatted_impact": format_currency(0.0),
            "urgent_count": 0,
            "summary": "No rows match current decision view.",
            "why_it_matters": "Adjust filters or refresh source data before assigning work.",
            "top_actions": [],
        }

    data = df.copy()
    impact_col, impact_total = _sum_first_existing_numeric(data, DECISION_BRIEF_IMPACT_COLUMNS)
    impact_label = DECISION_BRIEF_IMPACT_LABELS.get(impact_col or "", "Revenue Impact")
    urgent_count = _count_urgent_records(data)
    records = len(data)
    formatted_impact = format_currency(impact_total)

    summary = (
        f"{records} record(s) in {quick_view} with {impact_label.lower()} of "
        f"{formatted_impact} and {urgent_count} critical/high item(s)."
    )

    if impact_total > 0 and urgent_count > 0:
        why_it_matters = (
            f"Focus here first: urgent records carry {formatted_impact} in tracked exposure."
        )
    elif impact_total > 0:
        why_it_matters = f"Use this view to protect or capture {formatted_impact}."
    elif urgent_count > 0:
        why_it_matters = "Use this view to clear urgent operational risk."
    else:
        why_it_matters = "Use this view to assign owners and validate next operational actions."

    return {
        "title": title,
        "quick_view": quick_view,
        "records": records,
        "impact_label": impact_label,
        "impact_total": impact_total,
        "formatted_impact": formatted_impact,
        "urgent_count": urgent_count,
        "summary": summary,
        "why_it_matters": why_it_matters,
        "top_actions": _build_decision_brief_actions(data, max_items),
    }


def decision_brief_to_markdown(brief: dict[str, Any]) -> str:
    """Serialize a decision brief to Markdown for local handoff/export."""
    title = _clean_display_value(brief.get("title"), "Decision Brief")
    lines = [
        f"# {title}",
        "",
        f"- Quick view: {_clean_display_value(brief.get('quick_view'), 'All')}",
        f"- Records: {int(brief.get('records', 0) or 0)}",
        (
            f"- {_clean_display_value(brief.get('impact_label'), 'Revenue Impact')}: "
            f"{_clean_display_value(brief.get('formatted_impact'), '$0.00')}"
        ),
        f"- Critical/high items: {int(brief.get('urgent_count', 0) or 0)}",
        "",
        "## Summary",
        "",
        _clean_display_value(brief.get("summary"), "No summary available."),
        "",
        "## Why It Matters",
        "",
        _clean_display_value(brief.get("why_it_matters"), "No impact note available."),
    ]

    top_actions = brief.get("top_actions", [])
    if isinstance(top_actions, list) and top_actions:
        lines.extend(["", "## Top Actions", ""])
        for index, item in enumerate(top_actions, start=1):
            if not isinstance(item, dict):
                continue
            action_title = _clean_display_value(item.get("title"), "Record")
            action_text = _clean_display_value(item.get("action"), "Review record details.")
            owner = _clean_display_value(item.get("owner"), "Unassigned")
            status = _clean_display_value(item.get("status"), "Unscored")
            impact = _clean_display_value(item.get("impact"), "$0.00")
            lines.append(
                f"{index}. **{action_title}** - {action_text} "
                f"(owner: {owner}; status: {status}; impact: {impact})"
            )

    return "\n".join(lines).strip() + "\n"


def prepare_owner_workload_summary(
    df: pd.DataFrame | None,
    owner_columns: list[str] | None = None,
    impact_columns: list[str] | None = None,
    max_groups: int = 8,
) -> pd.DataFrame:
    """Summarize action workload by owner for dashboard handoff views."""
    columns = ["owner", "records", "critical_high", "impact_total"]
    if df is None or df.empty:
        return pd.DataFrame(columns=columns)

    data = df.copy()
    owner_col = _first_existing_column(
        data,
        owner_columns or ["suggested_owner", "owner", "metric_owner"],
    )
    if owner_col is None:
        return pd.DataFrame(columns=columns)

    impact_col = _first_existing_column(data, impact_columns or DECISION_BRIEF_IMPACT_COLUMNS)
    impact_values = (
        pd.to_numeric(data[impact_col], errors="coerce").fillna(0)
        if impact_col is not None
        else pd.Series(0.0, index=data.index)
    )

    grouped = pd.DataFrame(
        {
            "_owner": data[owner_col].apply(
                lambda value: _clean_display_value(value, "Unassigned")
            ),
            "_impact": impact_values,
            "_urgent": _urgent_record_mask(data),
        }
    )
    summary = (
        grouped.groupby("_owner", dropna=False)
        .agg(
            records=("_owner", "size"),
            critical_high=("_urgent", "sum"),
            impact_total=("_impact", "sum"),
        )
        .reset_index()
        .rename(columns={"_owner": "owner"})
    )
    summary["records"] = summary["records"].astype(int)
    summary["critical_high"] = summary["critical_high"].astype(int)
    summary["impact_total"] = summary["impact_total"].astype(float)

    return (
        summary.sort_values(
            ["critical_high", "impact_total", "records", "owner"],
            ascending=[False, False, False, True],
        )
        .head(max_groups)
        .reset_index(drop=True)
    )
