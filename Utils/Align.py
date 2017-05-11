import sys
import operator
import itertools

WEIGHTS = {"match":2, "mismatch":-2, "open":-1, "extend":-1}

###############################################################################
# Scoring Matrix
###############################################################################

def getGapScore(matrix, x, y, weights):
    # Based on the source element either the opening or extension penalty is used
    gap = "extend" if matrix[x][y][1] in ("open", "extend") else "open"
    return (matrix[x][y][0] + weights[gap], gap)

def getSimilarity(a, b):
    if a == b:
        return "match"
    else:
        return "mismatch"

def getBestMoveScore(matrix, x, y, stringA, stringB, weights):
    # The valid moves are diagonal, up and left
    # The diagonal move represents a match or a mismatch
    similarity = getSimilarity(stringA[x - 1], stringB[y - 1])
    scoreDiagonal = (matrix[x - 1][y - 1][0] + weights[similarity], similarity)
    # The up and left moves represent gaps in one of the strings
    scoreUp = getGapScore(matrix, x - 1, y, weights)
    scoreLeft = getGapScore(matrix, x, y - 1, weights)
    # The move with the highest score is used
    if scoreDiagonal[0] > scoreUp[0] and scoreDiagonal[0] > scoreLeft[0]:
        return scoreDiagonal
    elif scoreUp[0] > scoreLeft[0] and scoreUp[0] > scoreDiagonal[0]:
        return scoreUp
    else:
        return scoreLeft

def getDim(stringA, stringB):
    columns = len(stringA) + 1
    rows = len(stringB) + 1
    return columns, rows

def buildScoringMatrix(stringA, stringB, weights=None):
    global WEIGHTS
    if weights == None:
        weights = WEIGHTS
    columns, rows = getDim(stringA, stringB)
    matrix = [[None] * rows for x in range(columns)]
    # Initialize the (0,0) corner element
    matrix[0][0] = [0, "None"]
    # Initialize the elements of the top row and the left column
    for x in range(1, columns):
        matrix[x][0] = getGapScore(matrix, x - 1, 0, weights)
    for y in range(1, rows):
        matrix[0][y] = getGapScore(matrix, 0, y - 1, weights)
    # Calculate the scores for the inner elements
    for x in range(1, columns):
        for y in range(1, rows):
            matrix[x][y] = getBestMoveScore(matrix, x, y, stringA, stringB, weights)
    return matrix

###############################################################################
# NeedleMan-Wunsch Global Traversal
###############################################################################

def getTraversal(matrix):
    # Start from the lower right corner
    x = len(matrix) - 1
    y = len(matrix[0]) - 1
    # The traversal is a list of (x,y) element coordinates
    traversal = []
    # Find a path from the lower right corner to (0,0)
    while x != 0 or y != 0:
        traversal = [(x, y)] + traversal 
        x, y = move(matrix, x, y)
    return [(0, 0)] + traversal # The returned path starts from (0,0)

def move(matrix, x, y):
    moves = [(x-1, y-1), (x-1, y), (x, y-1)] # move diagonally, up, or left
    moves = [m for m in moves if m[0] >= 0 and m[1] >= 0] # limit moves to the matrix area
    values = [matrix[m[0]][m[1]][0] for m in moves] # count the values for the possible moves
    maxIndex, maxValue = max(enumerate(values), key=operator.itemgetter(1)) # select the move with the highest value
    return moves[maxIndex]

###############################################################################
# Traversal to Alignment
###############################################################################

def getAlignment(stringA, stringB, matrix, traversal):
    prevX = prevY = 0
    alignedA = []
    alignedB = []
    diff = ""
    posA = -1
    posB = -1
    offsets = [] # map of string B offsets to string A offsets
    for x, y in traversal[1:]:
        delta = (x - prevX, y - prevY)
        if delta == (1,1):
            posA += 1
            posB += 1
            alignedA.append(stringA[x - 1])
            alignedB.append(stringB[y - 1])
            diff += "*" if (stringA[x - 1] != stringB[y - 1]) else "|"
            offsets.append(posB)
        elif delta == (1,0):
            posB += 1
            alignedA.append(stringA[x - 1])
            alignedB.append("-")
            diff += "-"
            #offsets += [None]
        elif delta == (0,1):
            posA += 1
            alignedA.append("-")
            alignedB.append(stringB[y - 1])
            diff += "-"
            offsets += [None]
        else:
            raise Exception("Illegal move " + str(delta))
        prevX = x
        prevY = y
    if isinstance(stringA, basestring):
        assert isinstance(stringB, basestring)
        alignedA = "".join(alignedA)
        alignedB = "".join(alignedB)
    return alignedA, alignedB, diff, offsets

def fastAlign(target, source):
    i = j = 0
    fa = {"target":"", "source":"", "diff":"", "offsets":[]}
    while i < len(source):
        while i < len(source):
            a = source[i]
            b = target[j] if j < len(target) else None
            if a == b or (a.isspace() and (b == None or b.isspace())):
                fa["source"] += a
                fa["target"] += b if b != None else "-"
                fa["diff"] += "|"
                fa["offsets"] += [j] if b != None else [None]
            else:
                if not (a.isspace() or (b == None or b.isspace())):
                    return None
                break
            i += 1
            j += 1
        while i < len(source) and source[i].isspace():
            fa["source"] += source[i]
            fa["target"] += "-"
            fa["diff"] += "-"
            fa["offsets"] += [None]
            i += 1
        while j < len(target) and target[j].isspace():
            fa["source"] += "-"
            fa["target"] += target[j]
            fa["diff"] += "-"
            j += 1
    return fa

def align(stringA, stringB, weights=None, verbose=False):
    alignedA = alignedB = diff = offsets = traversal = None
    mode = None
    if stringA == stringB:
        alignedA = stringA
        alignedB = stringB
        diff = len(stringA) * "|"
        offsets = range(len(stringA))
        mode = "identical"
    if mode == None and isinstance(stringA, basestring) and isinstance(stringB, basestring):
        fa = fastAlign(stringA, stringB)
        if fa != None:
            mode = "fast"          
            alignedA = fa["target"]
            alignedB = fa["source"]
            diff = fa["diff"]
            offsets = fa["offsets"]
    if mode == None:
        mode = "matrix"
        matrix = buildScoringMatrix(stringA, stringB, weights)
        traversal = getTraversal(matrix)
        alignedA, alignedB, diff, offsets = getAlignment(stringA, stringB, matrix, traversal)
    if verbose:
        print >> sys.stderr, "alignment mode:", mode
        if traversal:
            print >> sys.stderr, traversal
        printAlignment(alignedA, alignedB, diff, offsets)
    return alignedA, alignedB, diff, offsets, mode
    
###############################################################################
# Visualization
###############################################################################

def printMatrix(matrix, stringA, stringB, traversal=None):
    columns, rows = getDim(stringA, stringB)
    cells = [" ", " "] + [char for char in stringA]
    charsB = [" "] + [char for char in stringB]
    for y in range(rows):
        cells += [charsB[y]]
        for x in range(columns):
            sep = " "
            if traversal != None and (x, y) in traversal:
                sep = "="
            cells.append(str(matrix[x][y][0]) + sep + ("*" if (matrix[x][y][1] == "mismatch") else matrix[x][y][1][0]))
    maxLen = max([len(x) for x in cells])
    s = ""
    for i in range(len(cells)):
        if s != "":
            s += " | "
        s += (maxLen - len(cells[i])) * " " + cells[i]
        if i > 0 and (i + 1) % (columns + 1) == 0:
            print >> sys.stderr, s
            s = ""

def printAlignment(alignedA, alignedB, diff, offsets=None):
    print >> sys.stderr, alignedA
    print >> sys.stderr, diff
    print >> sys.stderr, alignedB
    if offsets:
        print >> sys.stderr, offsets

if __name__=="__main__":
    from optparse import OptionParser
    optparser = OptionParser(description="")
    optparser.add_option("-a", default=None, help="")
    optparser.add_option("-b", default=None, help="")
    optparser.add_option("--match", default=WEIGHTS["match"], type=int, help="")
    optparser.add_option("--mismatch", default=WEIGHTS["mismatch"], type=int, help="")
    optparser.add_option("--open", default=WEIGHTS["open"], type=int, help="")
    optparser.add_option("--extend", default=WEIGHTS["extend"], type=int, help="")
    optparser.add_option("--words", default=False, action="store_true")
    optparser.add_option("--tryfast", default=False, action="store_true")
    (options, args) = optparser.parse_args()
    
    if options.words:
        options.a = options.a.split()
        options.b = options.b.split()
    weights = {k:getattr(options, k) for k in ("match", "mismatch", "open", "extend")}
    #weights["space"] = weights["mismatch"]
    align(options.a, options.b, weights, True)
#     matrix = buildScoringMatrix(options.a, options.b, weights)
#     traversal = getTraversal(matrix)
#     printMatrix(matrix, options.a, options.b, traversal)
#     print >> sys.stderr, traversal
#     printAlignment(*getAlignment(options.a, options.b, matrix, traversal))