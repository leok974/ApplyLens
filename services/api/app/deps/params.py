"""
Parameter validation and clamping utilities.
"""


def clamp_window_days(
    v: int | None, default: int = 30, mn: int = 1, mx: int = 365
) -> int:
    """
    Clamp window_days to a safe range.

    Args:
        v: Input value (can be None or invalid)
        default: Default value if v is None or invalid (default: 30)
        mn: Minimum allowed value (default: 1)
        mx: Maximum allowed value (default: 365)

    Returns:
        Clamped integer in range [mn, mx]

    Example:
        >>> clamp_window_days(None)
        30
        >>> clamp_window_days(500)
        365
        >>> clamp_window_days(-10)
        1
        >>> clamp_window_days(45)
        45
    """
    try:
        v = int(v or default)
    except (ValueError, TypeError):
        v = default
    return max(mn, min(v, mx))
