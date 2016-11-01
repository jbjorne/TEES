import sys
import operator

WEIGHTS = {"match":2, "mismatch":-2, "open":-1, "extend":0}

###############################################################################
# Scoring Matrix
###############################################################################

def getGapScore(matrix, x, y, weights):
    # Based on the source element either the opening or extension penalty is used
    gap = "extend" if matrix[x][y][1] in ("open", "extend") else "open"
    return (matrix[x][y][0] + weights[gap], gap)

def getBestMoveScore(matrix, x, y, stringA, stringB, weights):
    # The valid moves are diagonal, up and left
    # The diagonal move represents a match or a mismatch
    similarity = "match" if (stringA[x - 1] == stringB[y - 1]) else "mismatch"
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
    alignedA = ""
    alignedB = ""
    diff = ""
    posA = 0
    posB = 0
    offsets = [] # map of string B offsets to string A offsets
    for x, y in traversal[1:]:
        delta = (x - prevX, y - prevY)
        if delta == (1,1):
            posA += 1
            posB += 1
            alignedA += stringA[x - 1]
            alignedB += stringB[y - 1]
            diff += "*" if (stringA[x - 1] != stringB[y - 1]) else "|"
            offsets.append(posB)
        elif delta == (1,0):
            posB += 1
            alignedA += stringA[x - 1]
            alignedB += "-"
            diff += "-"
            #offsets += [None]
        elif delta == (0,1):
            posA += 1
            alignedA += "-"
            alignedB += stringB[y - 1]
            diff += "-"
            offsets += [None]
        else:
            raise Exception("Illegal move " + str(delta))
        prevX = x
        prevY = y
    return alignedA, alignedB, diff, offsets

###############################################################################
# Visualization
###############################################################################

def printMatrix(matrix, stringA, stringB, traversal=None):
    columns, rows = getDim(stringA, stringB)
    cells = [" ", " "] + [char for char in stringA]
    for y in range(rows):
        cells += [(" " + stringB)[y]]
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
            print s
            s = ""

def printAlignment(alignedA, alignedB, diff, offsets):
    print alignedA
    print diff
    print alignedB
    print offsets

if __name__=="__main__":
    from optparse import OptionParser
    optparser = OptionParser(description="")
    optparser.add_option("-a", default=None, help="")
    optparser.add_option("-b", default=None, help="")
    optparser.add_option("--match", default=WEIGHTS["match"], type=int, help="")
    optparser.add_option("--mismatch", default=WEIGHTS["mismatch"], type=int, help="")
    optparser.add_option("--open", default=WEIGHTS["open"], type=int, help="")
    optparser.add_option("--extend", default=WEIGHTS["extend"], type=int, help="")
    (options, args) = optparser.parse_args()
    
    weights = {k:getattr(options, k) for k in ("match", "mismatch", "open", "extend")}
    matrix = buildScoringMatrix(options.a, options.b, weights)
    traversal = getTraversal(matrix)
    printMatrix(matrix, options.a, options.b, traversal)
    print traversal
    printAlignment(*getAlignment(options.a, options.b, matrix, traversal))