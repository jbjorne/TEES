import random

def getSample(popSize, sampleFraction, seed=0):
    random.seed(seed)
    sample = random.sample( xrange(popSize), int(sampleFraction*float(popSize)) )
    vector = []
    for i in range(popSize):
        if i in sample:
            vector.append(0)
        else:
            vector.append(1)
    return vector

def getFolds(popSize, folds, seed=0):
    sampleSize = int(float(popSize) / float(folds))
    random.seed(seed)
    
    vector = []
    for i in range(popSize):
        vector.append(-1) # -1 is for items not in any fold
    
    population = range(popSize)
    for i in range(folds):
        sample = random.sample(population, sampleSize)
        for j in sample:
            vector[j] = i
            population.remove(j)
    # add -1 cases roughly evenly to all folds
    currentFold = 0
    for i in range(len(vector)):
        if vector[i] == -1:
            assert(currentFold < folds-1)
            vector[i] = currentFold
            currentFold += 1
    return vector

if __name__=="__main__":
    print "Testing 20, 0.0:"
    print getSample(20,0.0)
    print "Testing 20, 0.5:"
    print getSample(20,0.5)
    print "Folds 20 / 2:"
    print getFolds(20,2)
    print "Folds 20 / 3:"
    print getFolds(20,3)
    print "Folds 20 / 4:"
    print getFolds(20,4)
    print "Folds 20 / 20:"
    print getFolds(20,20)