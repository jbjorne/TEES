import random
from math import log

def scoreCand(table,candidate):
    """Score a single candidate using a sum. Candidate is a list of indices."""
    assert len(candidate)==len(table[0])
    return sum(log(table[row][col]) for col,row in enumerate(candidate))

def argmaxCol(table,col):
    """Index and value of the best row in a given column"""
    bestIdx=0
    bestVal=table[0][col]
    for idx in range(1,len(table)):
        if table[idx][col]>bestVal:
            bestIdx=idx
            bestVal=table[idx][col]
    return bestIdx,bestVal

def best(table):
    """A best candidate (out of the many possible)."""
    B=[]
    for col in range(len(table[0])):
        row,val=argmaxCol(table,col)
        B.append(row)
    return tuple(B)

def allMutations(table,candidate):
    """All candidates that can be obtained from this one by a one-point mutation"""
    result=[]
    candidate=list(candidate)
    for col in range(len(table[0])):
        for row in range(len(table)):
            if candidate[col]==row:
                continue #do not want to generate the same one again
            newCand=candidate[:]
            newCand[col]=row
            result.append((scoreCand(table,newCand),tuple(newCand)))
    assert len(result)==len(table[0])*(len(table)-1)
    return result

def decode(table,n):
    Q=[] #list of all open (score,candidate) pairs, sorted from lowest to highest score. Candidate is a list of indices.
    nbest=[] #list of n best (score,candidate) pairs -> the result of this function
    visited=set() #set of visited candidates -> this is, after all, only needed since different candidates can have the same score
    #initialize
    bestCand=best(table)
    visited.add(bestCand)
    Q.append((scoreCand(table,bestCand),bestCand))
    while len(Q)>0 and len(nbest)<n:
        #1) pop the best item from the open list
        score,candidate=Q.pop()
        nbest.append((score,candidate))
        #2) generate all possible next candidates
        nextCandidates=allMutations(table,candidate)
        for nextCScore,nextC in nextCandidates:
            if nextC in visited: #only consider those not yet visited
                continue
            Q.append((nextCScore,nextC)) #enqueue
            visited.add(nextC) #...and mark as visited
        Q.sort()
        if len(Q)>n: #the queue only needs to keep n items at a time (actually I think only n-len(nbest)...?)
            Q=Q[len(Q)-n:]
    return nbest

############### TESTING ONLY ##################
def allSequences(numRow,numCol):
    oneCol=[[row] for row in range(numRow)]
    if numCol==1:
        return oneCol
    else:
        result=[]
        oneShorter=allSequences(numRow,numCol-1)
        for c in oneCol:
            for s in oneShorter:
                result.append(s+c)
        return result

def bruteForceDecode(table,n):
    allC=allSequences(len(table),len(table[0]))
    assert len(allC)==len(table)**len(table[0])
    allCScored=[(scoreCand(table,cand),cand) for cand in allC]
    allCScored.sort(reverse=True)
    return allCScored[:n]

def test(rows,cols,n):
    #get me an nxm table with random numbers
    table=[[random.randint(0,5) for col in range(cols)] for row in range(rows)] #set a low number in randint() to induce score ties
    nbestBrute=bruteForceDecode(table,n)
    nbestQ=decode(table,n)
    assert nbestQ[-1][0]==nbestBrute[-1][0] #The worst scores given must be equal
    assert nbestQ[0][0]==nbestBrute[0][0] #the best scores must be equal
    for idx in range(1,n):
        assert nbestQ[idx-1][0]>=nbestQ[idx][0] #The scores given must be in nonincreasing order
        assert nbestBrute[idx-1][0]>=nbestBrute[idx][0]
    candSet=set()
    #no candidate is repeated in the n best
    for score,cand in nbestQ:
        assert tuple(cand) not in candSet
        candSet.add(tuple(cand))
    print nbestQ
    print "Test passed"

#test(5,7,50)
