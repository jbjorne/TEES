def overlap(range1, range2):
    """ Checks whether two ranges (f.e. characted offsets overlap)
    
    Keyword arguments:
    range1 -- a tuple where range1[0] <= range1[1]
    range1 -- a tuple where range2[0] <= range2[1]
    
    Returns:
    True (ranges overlap) or False (no overlap)
    """
    assert(range1[0] <= range1[1])
    assert(range2[0] <= range2[1])
    # Fully overlapping cases:
    # x1 <= y1 <= y2 <= x2
    # y1 <= x1 <= x2 <= y2
    # Partially overlapping cases:
    # x1 <= y1 <= x2 <= y2
    # y1 <= x1 <= y2 <= x2
    # Non-overlapping cases:
    # x1 <= x2 < y1 <= y2
    # y1 <= y2 < x1 <= x2
    return not (range1[1] < range2[0] or range2[1] < range1[0])
