from typing import Any, List, Mapping


def safe_get(mapping: Mapping[Any, Any] | None, key: Any, default: Any = None) -> Any:
    if mapping is None:
        return default
    return mapping.get(key, default)


def normalize_column_name(name: str) -> str:
    if not name:
        return ""
    return name.strip().lower().replace(" ", "_")


def normalize_column_names(columns: List[str]) -> List[str]:
    return [normalize_column_name(c) for c in columns]


def ensure_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, (tuple, set)):
        return list(value)
    return [value]


def format_percentage(value: float | None, decimals: int = 2) -> str:
    if value is None:
        return ""
    return f"{value * 100:.{decimals}f}%"


def format_currency(value: float | None, symbol: str = "$", decimals: int = 2) -> str:
    if value is None:
        return ""
    if value < 0:
        return f"-{symbol}{abs(value):.{decimals}f}"
    return f"{symbol}{value:.{decimals}f}"
