def charOffsetToTuples(charOffset):
    """ Splits a comma separated list of character offsets into tuples of integers.

    Keyword arguments:
    charOffset -- a string in the format "0-2,5-20"
    
    Returns:
    A list of tuples of two integers each
    """
    tuples = []
    ranges = charOffset.split(",")
    for r in ranges:
        numbers = r.split("-")
        tuples.append( (int(numbers[0]),int(numbers[1])) )
    return tuples

def overlap(range1, range2):
    """ Checks whether two ranges (f.e. character offsets overlap)
    
    This snippet by Steven D'Aprano is from the forum of
    www.thescripts.com.
    
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
