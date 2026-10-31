def overlap_length(a_start, a_end, b_start, b_end):
    """Return the nonnegative length shared by two ordered intervals."""
    return max(0, min(a_end, b_end) - max(a_start, b_start))
