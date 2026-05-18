"""
business_health_score.py — Composite Business Health Score Engine.

Combines seven analytical domains into a single structured health assessment.

Design contract:
    - Each domain score is 0–100 (100 = perfectly healthy).
    - Scores are derived from deterministic thresholds; no ML.
    - The composite score is a simple equal-weight average.
    - Status bands are deterministic from the composite score.
    - Output is a list of AreaScore records and one CompositeScore.

Status bands:
    Healthy  ≥ 80
    Stable   ≥ 65
    Watch    ≥ 50
    Risk     ≥ 30
    Critical <  30
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core.business_health._utils import clamp_score, safe_divide


# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------

_HEALTHY_THRESHOLD: float = 80.0
_STABLE_THRESHOLD: float = 65.0
_WATCH_THRESHOLD: float = 50.0
_RISK_THRESHOLD: float = 30.0


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass
class AreaScore:
    """Health score for a single analytical domain."""

    area: str
    score: float  # 0–100
    status: str  # Healthy | Stable | Watch | Risk | Critical
    explanation: str
    inputs: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CompositeScore:
    """Aggregated business health score across all domains."""

    composite_score: float
    status: str
    area_scores: List[AreaScore] = field(default_factory=list)
    explanation: str = ""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _status_from_score(score: float) -> str:
    """Map a 0–100 score to a status label."""
    if score >= _HEALTHY_THRESHOLD:
        return "Healthy"
    if score >= _STABLE_THRESHOLD:
        return "Stable"
    if score >= _WATCH_THRESHOLD:
        return "Watch"
    if score >= _RISK_THRESHOLD:
        return "Risk"
    return "Critical"


def _score_ratio(value: float, target: float, inverse: bool = False) -> float:
    """
    Convert a ratio-style metric to a 0–100 score.

    For normal metrics (higher = better):
        score = min(value / target, 1.0) × 100

    For inverse metrics (lower = better):
        score = max(1 - value / target, 0.0) × 100

    target must be non-zero; if zero, returns 50.0 (neutral).
    """
    if not target:
        return 50.0
    if inverse:
        raw = max(0.0, 1.0 - value / target)
    else:
        raw = min(1.0, value / target)
    return clamp_score(raw * 100)


# ---------------------------------------------------------------------------
# Domain scorers
# ---------------------------------------------------------------------------


def score_profitability(
    gross_margin: float,
    operating_margin: float,
    net_margin: float,
) -> AreaScore:
    """
    Profitability score — weighted blend of three margin metrics.

    Targets (SaaS benchmarks):
        gross_margin    ≥ 0.70  → full score
        operating_margin ≥ 0.20 → full score
        net_margin      ≥ 0.10  → full score
    """
    gm_score = _score_ratio(gross_margin, 0.70)
    om_score = _score_ratio(operating_margin, 0.20)
    nm_score = _score_ratio(net_margin, 0.10)
    # Gross margin weighted most heavily
    score = clamp_score(gm_score * 0.5 + om_score * 0.3 + nm_score * 0.2)
    status = _status_from_score(score)
    return AreaScore(
        area="profitability",
        score=round(score, 2),
        status=status,
        explanation=(
            f"Gross margin {gross_margin:.1%}, operating margin {operating_margin:.1%}, "
            f"net margin {net_margin:.1%}."
        ),
        inputs={
            "gross_margin": gross_margin,
            "operating_margin": operating_margin,
            "net_margin": net_margin,
        },
    )


def score_revenue_health(
    revenue_growth_rate: float,
    recurring_revenue_ratio: float,
    refund_rate: float,
    failed_payment_rate: float,
) -> AreaScore:
    """
    Revenue health score.

    Targets:
        revenue_growth_rate      ≥ 0.20/yr  → full score
        recurring_revenue_ratio  ≥ 0.80     → full score
        refund_rate              ≤ 0.02     → full score (inverse)
        failed_payment_rate      ≤ 0.03     → full score (inverse)
    """
    growth_score = _score_ratio(revenue_growth_rate, 0.20)
    recur_score = _score_ratio(recurring_revenue_ratio, 0.80)
    refund_score = _score_ratio(refund_rate, 0.02, inverse=True)
    failed_score = _score_ratio(failed_payment_rate, 0.03, inverse=True)
    score = clamp_score(
        growth_score * 0.35 + recur_score * 0.35 + refund_score * 0.15 + failed_score * 0.15
    )
    status = _status_from_score(score)
    return AreaScore(
        area="revenue",
        score=round(score, 2),
        status=status,
        explanation=(
            f"Growth {revenue_growth_rate:.1%}, recurring ratio {recurring_revenue_ratio:.1%}, "
            f"refund rate {refund_rate:.1%}, failed payment rate {failed_payment_rate:.1%}."
        ),
        inputs={
            "revenue_growth_rate": revenue_growth_rate,
            "recurring_revenue_ratio": recurring_revenue_ratio,
            "refund_rate": refund_rate,
            "failed_payment_rate": failed_payment_rate,
        },
    )


def score_cashflow(runway_months: float, free_cash_flow: float) -> AreaScore:
    """
    Cash flow score.

    Targets:
        runway_months  ≥ 18 months → full score
        free_cash_flow ≥ 0         → full score bonus
    """
    runway_score = _score_ratio(runway_months, 18.0)
    # Positive FCF adds a bonus cap of 20 points; negative subtracts up to 20
    if free_cash_flow >= 0:
        fcf_bonus = min(20.0, free_cash_flow / 10_000 * 20)
    else:
        fcf_bonus = max(-20.0, free_cash_flow / 10_000 * 20)
    score = clamp_score(runway_score + fcf_bonus)
    status = _status_from_score(score)
    return AreaScore(
        area="cashflow",
        score=round(score, 2),
        status=status,
        explanation=(f"Runway {runway_months:.1f} months; free cash flow ${free_cash_flow:,.0f}."),
        inputs={"runway_months": runway_months, "free_cash_flow": free_cash_flow},
    )


def score_unit_economics(ltv_to_cac: float, cac_payback_months: float) -> AreaScore:
    """
    Unit economics score.

    Targets:
        ltv_to_cac       ≥ 3.0   → full score
        cac_payback      ≤ 12 mo → full score (inverse: lower is better)
    """
    ltv_score = _score_ratio(ltv_to_cac, 3.0)
    payback_score = _score_ratio(cac_payback_months, 12.0, inverse=True)
    score = clamp_score(ltv_score * 0.6 + payback_score * 0.4)
    status = _status_from_score(score)
    return AreaScore(
        area="unit_economics",
        score=round(score, 2),
        status=status,
        explanation=(
            f"LTV:CAC ratio {ltv_to_cac:.2f}x; CAC payback {cac_payback_months:.1f} months."
        ),
        inputs={"ltv_to_cac": ltv_to_cac, "cac_payback_months": cac_payback_months},
    )


def score_growth(
    customer_growth_rate: float,
    revenue_growth_rate: float,
    growth_efficiency: float,
) -> AreaScore:
    """
    Growth quality score.

    Targets:
        customer_growth_rate  ≥ 0.10/period → full score
        revenue_growth_rate   ≥ 0.20/period → full score
        growth_efficiency     ≥ 1.0         → full score
    """
    cust_score = _score_ratio(customer_growth_rate, 0.10)
    rev_score = _score_ratio(revenue_growth_rate, 0.20)
    eff_score = _score_ratio(growth_efficiency, 1.0)
    score = clamp_score(cust_score * 0.35 + rev_score * 0.40 + eff_score * 0.25)
    status = _status_from_score(score)
    return AreaScore(
        area="growth",
        score=round(score, 2),
        status=status,
        explanation=(
            f"Customer growth {customer_growth_rate:.1%}, "
            f"revenue growth {revenue_growth_rate:.1%}, "
            f"growth efficiency {growth_efficiency:.2f}x."
        ),
        inputs={
            "customer_growth_rate": customer_growth_rate,
            "revenue_growth_rate": revenue_growth_rate,
            "growth_efficiency": growth_efficiency,
        },
    )


def score_efficiency(
    revenue_per_employee: float,
    sales_efficiency: float,
) -> AreaScore:
    """
    Operational efficiency score.

    Targets:
        revenue_per_employee  ≥ $150,000  → full score (SaaS benchmark)
        sales_efficiency      ≥ 1.0       → full score
    """
    rpe_score = _score_ratio(revenue_per_employee, 150_000)
    se_score = _score_ratio(sales_efficiency, 1.0)
    score = clamp_score(rpe_score * 0.5 + se_score * 0.5)
    status = _status_from_score(score)
    return AreaScore(
        area="efficiency",
        score=round(score, 2),
        status=status,
        explanation=(
            f"Revenue per employee ${revenue_per_employee:,.0f}; "
            f"sales efficiency {sales_efficiency:.2f}x."
        ),
        inputs={
            "revenue_per_employee": revenue_per_employee,
            "sales_efficiency": sales_efficiency,
        },
    )


def score_risk(
    customer_concentration: float,
    churn_exposure: float,
    cashflow_risk_score: float,
) -> AreaScore:
    """
    Risk domain score — lower raw risk metrics produce higher scores.

    Targets (inverse: lower = better):
        customer_concentration  ≤ 0.10  → full score
        churn_exposure          ≤ 0.05  → full score
        cashflow_risk_score     ≤ 20    → full score (already 0-100)
    """
    conc_score = _score_ratio(customer_concentration, 0.10, inverse=True)
    churn_score = _score_ratio(churn_exposure, 0.05, inverse=True)
    # cashflow_risk_score is already 0–100 where 0 = best; invert for health scale
    cf_score = clamp_score(100.0 - cashflow_risk_score)
    score = clamp_score(conc_score * 0.35 + churn_score * 0.35 + cf_score * 0.30)
    status = _status_from_score(score)
    return AreaScore(
        area="risk",
        score=round(score, 2),
        status=status,
        explanation=(
            f"Customer concentration {customer_concentration:.1%}, "
            f"churn exposure {churn_exposure:.1%}, "
            f"cashflow risk {cashflow_risk_score:.0f}/100."
        ),
        inputs={
            "customer_concentration": customer_concentration,
            "churn_exposure": churn_exposure,
            "cashflow_risk_score": cashflow_risk_score,
        },
    )


# ---------------------------------------------------------------------------
# Engine class
# ---------------------------------------------------------------------------


class BusinessHealthScoreEngine:
    """
    Combines domain area scores into a composite business health assessment.

    Usage
    -----
    engine = BusinessHealthScoreEngine()
    result = engine.calculate(
        profitability_inputs={...},
        revenue_inputs={...},
        cashflow_inputs={...},
        unit_economics_inputs={...},
        growth_inputs={...},
        efficiency_inputs={...},
        risk_inputs={...},
    )
    """

    def calculate(
        self,
        profitability_inputs: Optional[Dict[str, float]] = None,
        revenue_inputs: Optional[Dict[str, float]] = None,
        cashflow_inputs: Optional[Dict[str, float]] = None,
        unit_economics_inputs: Optional[Dict[str, float]] = None,
        growth_inputs: Optional[Dict[str, float]] = None,
        efficiency_inputs: Optional[Dict[str, float]] = None,
        risk_inputs: Optional[Dict[str, float]] = None,
    ) -> CompositeScore:
        """
        Calculate the composite business health score from seven domain inputs.

        All input dicts use float values matching the domain scorer parameters.
        Missing or None dicts are substituted with neutral defaults (score = 50).
        """
        area_scores: List[AreaScore] = []

        # Profitability
        pi = profitability_inputs or {}
        area_scores.append(
            score_profitability(
                gross_margin=pi.get("gross_margin", 0.0),
                operating_margin=pi.get("operating_margin", 0.0),
                net_margin=pi.get("net_margin", 0.0),
            )
        )

        # Revenue
        ri = revenue_inputs or {}
        area_scores.append(
            score_revenue_health(
                revenue_growth_rate=ri.get("revenue_growth_rate", 0.0),
                recurring_revenue_ratio=ri.get("recurring_revenue_ratio", 0.0),
                refund_rate=ri.get("refund_rate", 0.0),
                failed_payment_rate=ri.get("failed_payment_rate", 0.0),
            )
        )

        # Cash flow
        ci = cashflow_inputs or {}
        area_scores.append(
            score_cashflow(
                runway_months=ci.get("runway_months", 0.0),
                free_cash_flow=ci.get("free_cash_flow", 0.0),
            )
        )

        # Unit economics
        ue = unit_economics_inputs or {}
        area_scores.append(
            score_unit_economics(
                ltv_to_cac=ue.get("ltv_to_cac", 0.0),
                cac_payback_months=ue.get("cac_payback_months", 0.0),
            )
        )

        # Growth
        gi = growth_inputs or {}
        area_scores.append(
            score_growth(
                customer_growth_rate=gi.get("customer_growth_rate", 0.0),
                revenue_growth_rate=gi.get("revenue_growth_rate", 0.0),
                growth_efficiency=gi.get("growth_efficiency", 0.0),
            )
        )

        # Efficiency
        ei = efficiency_inputs or {}
        area_scores.append(
            score_efficiency(
                revenue_per_employee=ei.get("revenue_per_employee", 0.0),
                sales_efficiency=ei.get("sales_efficiency", 0.0),
            )
        )

        # Risk
        rki = risk_inputs or {}
        area_scores.append(
            score_risk(
                customer_concentration=rki.get("customer_concentration", 0.0),
                churn_exposure=rki.get("churn_exposure", 0.0),
                cashflow_risk_score=rki.get("cashflow_risk_score", 100.0),
            )
        )

        composite = safe_divide(sum(a.score for a in area_scores), len(area_scores))
        composite = round(clamp_score(composite), 2)
        status = _status_from_score(composite)

        weakest = min(area_scores, key=lambda a: a.score)
        return CompositeScore(
            composite_score=composite,
            status=status,
            area_scores=area_scores,
            explanation=(
                f"Composite score {composite:.1f}/100 ({status}). "
                f"Weakest area: {weakest.area} ({weakest.score:.1f})."
            ),
        )
