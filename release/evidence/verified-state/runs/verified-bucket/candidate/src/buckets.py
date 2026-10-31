def bucket_index(value, width):
    """Return the zero-based bucket for nonnegative value and positive width."""
    return int(value // width)
