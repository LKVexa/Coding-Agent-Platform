def clamp(value, lo, hi):
    """Return value limited to the inclusive interval lo..hi (lo <= hi)."""
    if value < lo:
        return lo
    if value > hi:
        return hi
    return value
