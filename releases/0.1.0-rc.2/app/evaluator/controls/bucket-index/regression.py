def bucket_index(value, width):
    result = int(value // width)
    if value > 0 and value % width == 0:
        return result - 1
    return result
