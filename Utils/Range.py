"""
Character offset tools.
"""
__version__ = "$Revision: 1.11 $"

import types

def merge(range1, range2):
    mergedRange = [0,0]
    assert(overlap(range1, range2))
    if range1[0] < range2[0]:
        mergedRange[0] = range1[0]
    else:
        mergedRange[0] = range2[0]
    if range1[1] > range2[1]:
        mergedRange[1] = range1[1]
    else:
        mergedRange[1] = range2[1]
    return (mergedRange[0],mergedRange[1])

def charOffsetToSingleTuple(charOffset, offsetSep="-"):
    tuples = charOffsetToTuples(charOffset, offsetSep)
    assert len(tuples) == 1, charOffset
    return tuples[0] 

def charOffsetToTuples(charOffset, offsetSep="-", rangeSep=","):
    """ Splits a comma separated list of character offsets into tuples of integers.

    Keyword arguments:
    charOffset -- a string in the format "0-2,5-20"
    
    Returns:
    A list of tuples of two integers each
    """
    tuples = []
    ranges = charOffset.split(rangeSep)
    for r in ranges:
        begin, end = r.strip().split(offsetSep)
        tuples.append( (int(begin),int(end)) )
    return tuples

def contains(range1, range2):
    if range1[0] <= range2[0] and range1[1] >= range2[1]:
        return True
    else:
        return False

def length(range):
    return range[1] - range[0] # + 1

def mismatch(range1, range2):
    l1 = length(range1)
    l2 = length(range2)
    if contains(range1, range2):
        return l1 - l2
    elif contains(range2, range1):
        return l2 - l1
    elif overlap(range1, range2):
        if range1[1] >= range2[0]:
            return length( (range1[0], range2[1]) )
        else: # range2[0] >= range1[1]
            return length( (range2[0], range1[1]) )
    else:
        return l1 + l2

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
    assert(range1[0] <= range1[1]), (range1, range2)
    assert(range2[0] <= range2[1]), (range1, range2)
    # Fully overlapping cases:
    # x1 <= y1 <= y2 <= x2
    # y1 <= x1 <= x2 <= y2
    # Partially overlapping cases:
    # x1 <= y1 <= x2 <= y2
    # y1 <= x1 <= y2 <= x2
    # Non-overlapping cases:
    # x1 <= x2 < y1 <= y2
    # y1 <= y2 < x1 <= x2
    return not (range1[1] <= range2[0] or range2[1] <= range1[0])

def order(range1, range2):
    if range1[0] < range2[0]:
        return -1
    elif range1[0] > range2[0]:
        return 1
    elif range1[1] < range2[1]: # here range1[0] == range2[0]
        return -1
    elif range1[1] > range2[1]: # here range1[0] == range2[0]
        return 1
    else: # ranges are equal
        return 0

def tuplesToCharOffset(tuples, offsetSep="-", rangeSep=","):
    if len(tuples) == 2 and type(tuples[0]) == types.IntType and type(tuples[1]) == types.IntType:
        tuples = [tuples]
    charOffset = ""
    isFirst = True
    for tup in tuples:
        if not isFirst:
            charOffset += rangeSep
        charOffset += str(tup[0]) + offsetSep + str(tup[1])
        isFirst = False
    return charOffset