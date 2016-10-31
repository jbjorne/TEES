WEIGHTS = {"match":2, "mismatch":-1, "gap":-1}

def getScore(matrix, x, y, stringA, stringB, weights):
    similarity = weights["match"] if (stringA[x-1] == stringB[y - 1]) else weights["mismatch"]
    
    scoreDiagonal = matrix[x - 1][y - 1] + similarity
    scoreUp   = matrix[x - 1][y] + weights["gap"]
    scoreLeft = matrix[x][y - 1] + weights["gap"]
    return max(0, scoreDiagonal, scoreUp, scoreLeft)

def initMatrix(stringA, stringB, weights):
    matrix = [[None] * (len(stringB) + 1) for i in range(len(stringA) + 1)]
    matrix[0][0] = 0
    weight = -1
    for i in range(1, len(stringB) + 1):
        matrix[0][i] = weight
        weight -= 1
    weight = -1
    for i in range(1, len(stringB) + 1):
        matrix[i][0] = weight
        weight -= 1
    for i in range(1, len(stringA) + 1):
        for j in range(1, len(stringB) + 1):
            matrix[i][j] = getScore(matrix, i, j, stringA, stringB, weights)
    return matrix

def getAlignment(matrix):
    pos = (len(matrix[0]) - 1, len(matrix) - 1) # lower right corner
    alignment = []
    while pos != (0, 0):
        alignment = [pos] + alignment 
        pos = move(matrix, pos)
    return [pos] + alignment

def move(matrix, pos):
    moves = [(-1, -1), (-1, 0), (0, -1)] # move diagonally, up, or left
    values = [(matrix[pos[0] + m[0]][pos[1] + m[1]], m) for m in moves]
    bestMove = sorted(values, reverse=True)[0][1]
    return (pos[0] + bestMove[0], pos[1] + bestMove[1])

def printMatrix(matrix):
    for row in matrix:
        print row

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
    printMatrix(matrix)
    alignment = getAlignment(matrix)
    print alignment
    printAlignment(options.a, options.b, matrix, alignment)