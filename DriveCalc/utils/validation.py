"""Input validation utilities for DriveCalc."""
from typing import Optional


def require_positive(value: float, name: str) -> Optional[str]:
    if value <= 0:
        return f"{name} must be positive (got {value})."
    return None


def require_non_negative(value: float, name: str) -> Optional[str]:
    if value < 0:
        return f"{name} must be ≥ 0 (got {value})."
    return None


def require_range(value: float, lo: float, hi: float, name: str) -> Optional[str]:
    if not (lo <= value <= hi):
        return f"{name} must be between {lo} and {hi} (got {value})."
    return None


def require_integer_positive(value: int, name: str) -> Optional[str]:
    if value < 1:
        return f"{name} must be a positive integer (got {value})."
    return None


def collect_errors(*results) -> list[str]:
    return [r for r in results if r is not None]
