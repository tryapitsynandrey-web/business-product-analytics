"""
_utils.py — Shared arithmetic helpers for the business_health package.

All functions are pure, deterministic, and free of side effects.
"""

from __future__ import annotations


def safe_divide(numerator: float, denominator: float, fallback: float = 0.0) -> float:
    """Return numerator / denominator, or fallback when denominator is zero or None."""
    if not denominator:
        return fallback
    return numerator / denominator


def percentage_change(current: float, previous: float) -> float:
    """
    Return the percentage change from previous to current.

    Returns 0.0 when previous is zero (avoids divide-by-zero).
    Positive result means growth; negative means contraction.
    """
    if not previous:
        return 0.0
    return (current - previous) / abs(previous)


def clamp_score(value: float, min_value: float = 0.0, max_value: float = 100.0) -> float:
    """Clamp a numeric score to [min_value, max_value]."""
    return max(min_value, min(max_value, value))
