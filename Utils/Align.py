import sys
import operator

WEIGHTS = {"match":2, "mismatch":-1, "gap":-1}

def getScore(matrix, x, y, stringA, stringB, weights):
    similarity = weights["match"] if (stringA[x - 1] == stringB[y - 1]) else weights["mismatch"]
    
    scoreDiagonal = matrix[x - 1][y - 1] + similarity
    scoreUp = matrix[x - 1][y] + weights["gap"]
    scoreLeft = matrix[x][y - 1] + weights["gap"]
    return max(0, scoreDiagonal, scoreUp, scoreLeft)

def getDim(stringA, stringB):
    columns = len(stringA) + 1
    rows = len(stringB) + 1
    return columns, rows

def initMatrix(stringA, stringB, weights):
    columns, rows = getDim(stringA, stringB)
    matrix = [[None] * rows for x in range(columns)]
    matrix[0][0] = 0
    for x in range(columns):
        matrix[x][0] = -x
    for y in range(rows):
        matrix[0][y] = -y
    for x in range(1, columns):
        for y in range(1, rows):
            matrix[x][y] = getScore(matrix, x, y, stringA, stringB, weights)
    return matrix

def getAlignment(matrix):
    # Start from the lower right corner
    x = len(matrix) - 1
    y = len(matrix[0]) - 1
    alignment = []
    while x != 0 or y != 0:
        alignment = [(x, y)] + alignment 
        x, y = move(matrix, x, y)
    return [(0, 0)] + alignment

def move(matrix, x, y):
    moves = [(x-1, y-1), (x-1, y), (x, y-1)] # move diagonally, up, or left
    moves = [m for m in moves if m[0] >= 0 and m[1] >= 0] # limit to matrix area
    values = [matrix[m[0]][m[1]] for m in moves]
    maxIndex, maxValue = max(enumerate(values), key=operator.itemgetter(1))
    return moves[maxIndex]

def printMatrix(matrix, stringA, stringB):
    columns, rows = getDim(stringA, stringB)
    print "  " + str([char for char in (" " + stringA)]).replace("'", "")
    for y in range(rows):
        print (" " + stringB)[y], [matrix[x][y] for x in range(columns)]

def printAlignment(stringA, stringB, matrix, alignment):
    prevPos = (0, 0)
    alignedA = ""
    alignedB = ""
    for pos in alignment[1:]:
        delta = (pos[0] - prevPos[0], pos[1] - prevPos[1])
        if delta == (1,1):
            alignedA += stringA[pos[0] - 1]
            alignedB += stringB[pos[1] - 1]
        elif delta == (1,0):
            alignedA += stringA[pos[0] - 1]
            alignedB += "-"
        elif delta == (0,1):
            alignedA += "-"
            alignedB += stringB[pos[1] - 1]
        else:
            raise Exception("Illegal move " + str(delta))
        prevPos = pos
    print alignedA
    print alignedB

if __name__=="__main__":
    from optparse import OptionParser
    optparser = OptionParser(description="")
    optparser.add_option("-a", default=None, help="")
    optparser.add_option("-b", default=None, help="")
    (options, args) = optparser.parse_args()
    
    matrix = initMatrix(options.a, options.b, WEIGHTS)
    printMatrix(matrix, options.a, options.b)
    alignment = getAlignment(matrix)
    print alignment
    printAlignment(options.a, options.b, matrix, alignment)