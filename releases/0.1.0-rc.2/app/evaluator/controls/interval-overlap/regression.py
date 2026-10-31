def overlap_length(a_start, a_end, b_start, b_end):
    if a_end <= b_start or b_end <= a_start:
        return 0
    return a_end - a_start
