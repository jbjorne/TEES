import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/..")
from Core.IdSet import IdSet
from operator import itemgetter
try:
    import numpy
    numpy.array([])
    numpyAvailable = True
except:
    numpyAvailable = False

def writeModel(svs, modelfile, newfile, tokenized=False):
    f = open(modelfile,"rt")
    lines = f.readlines()
    f.close()
    
    if tokenized:
        fline = "1\nqid:0"
    else:
        fline = "1 qid:0"
    index = 1
    for sv in svs:
        for feature in sv:
            if feature != 0:
                if tokenized:
                    fline += "\n"
                else:
                    fline += " "
                fline += str(index) + ":" + feature
            index += 1
    if tokenized:
        lines[-1] = fline + "\n#\n"
    else:
        lines[-1] = fline + " #"
    
    f = open(newfile, "wt")
    for line in lines:
        f.write(line)
    f.close()

def tokenizeModel(modelfile, newfile):
    f = open(modelfile,"rt")
    lines = f.readlines()
    f.close()
    lastLine = lines[-1]
    lines = lines[:-1]
        
    f = open(newfile, "wt")
    for line in lines:
        f.write(line)
    for token in lastLine.split():
        f.write(token + "\n")
    f.close()

def parseModel(modelfile):
    f = open(modelfile,"rt")
    for line in f:
        if line.find("number of classes") != -1:
            numClasses = int(line.split("#")[0])
        elif line.find("number of base features") != -1:
            numFeatures = int(line.split("#")[0])
        elif line.find("highest feature index") != -1:
            highestIndex = int(line.split("#")[0])
    f.close()
    return numClasses, numFeatures, highestIndex

def getSupportVectors(modelfile, valueToFloat=True):
    numClasses, numFeatures, highestIndex = parseModel(modelfile)
    #print numClasses, numFeatures, highestIndex
    
    f = open(modelfile,"rt")
    line = f.readlines()[-1]
    f.close()
    line = line.rsplit("#",1)[0]
    tokens = line.split()
    assert tokens[1].find("qid") != -1
    tokens = tokens[2:]
    numFeaturesPerClass = highestIndex / numClasses
    
    svs = [[]]
    svIndex = 0
    num = 0
    for token in tokens:
        newNum, value = token.split(":")
        newNum = int(newNum)
        if valueToFloat:
            value = float(value)
        assert newNum > num
        while newNum - num > 1:
            svs[-1].append(0)
            if len(svs[-1]) == numFeaturesPerClass:
                svs.append([])
            num += 1
        svs[-1].append(value)
        if len(svs[-1]) == numFeaturesPerClass:
            svs.append([])
        num = newNum
    while num < highestIndex - 1:
        svs[-1].append(0)
        num += 1
    #print len(svs)
    if numpyAvailable:
        for i in range(len(svs)):
            svs[i] = numpy.array(svs[i])
    #for i in range(len(svs)):
    #    print len(svs[i])
    return svs

def getSupportVectorsTest(line, numClasses, numFeatures=-1):
    print line[-500:]
    line = line.rsplit("#",1)[0]
    print line[-500:]
    tokens = line.split()
    assert tokens[1].find("qid") != -1
    tokens = tokens[2:]
    num = 0
    realTokens = 0
    for token in tokens:
        newNum = int(token.split(":")[0])
        #assert newNum == num + 1, str(newNum) + " " + str(num)
        if newNum - num > 1:
            pass
            #print "gap", newNum - num
        realTokens += newNum - num
        num = newNum
    print "r", realTokens, realTokens/numClasses
    if numFeatures != -1:
        print "Classes", numClasses
        print "Features:", numFeatures
        print "Tokens:", len(tokens), "Classes*features:", numClasses * numFeatures
        assert len(tokens) == numClasses * numFeatures

def mapIds(featureIds, modelFile):
    f = open(modelFile,"rt")
    for line in f:
        if line.find("number of classes") != -1:
            numClasses = int(line.split("#")[0])
        elif line.find("number of base features") != -1:
            numFeatures = int(line.split("#")[0])
        elif line.find("qid") != -1:
            features = getSupportVectorsTest(line, numClasses, numFeatures)
    f.close()

def getWeights(svs):
    numFeatures = len(svs[0])
    #print numFeatures
    weights = [0]
    for i in range(numFeatures):
        for sv in svs:
            #print len(sv)
            assert len(sv) == numFeatures, (len(sv), numFeatures)
            absFeature = abs(sv[i])
            if absFeature > weights[-1]:
                weights[-1] = absFeature
        weights.append(0)
    return weights

def getWeightsPosNeg(svs):
    numFeatures = len(svs[0])
    #print numFeatures
    weights = [0]
    for i in range(numFeatures):
        for sv in svs:
            #print len(sv)
            assert len(sv) == numFeatures
            absFeature = abs(sv[i])
            if absFeature > weights[-1]:
                weights[-1] = absFeature
        weights.append(0)
    return weights

def assignNames(weights, featureIds):
    tuples = []
    for i in range(len(weights)):
        tuples.append( (weights[i], featureIds.getName(i+1)) )
    tuples.sort(key=itemgetter(0))
    return tuples

def getTokenWeights(weights):
    dict = {}
    for pair in weights:
        tokens = pair[1].split("_")
        for token in tokens:
            if not dict.has_key(token):
                dict[token] = 0
            if pair[0] > dict[token]:
                dict[token] = pair[0]
    return dict

if __name__=="__main__":
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"
    
    #classIds = IdSet(filename="/usr/share/biotext/GeniaChallenge/extension-data/genia/edge-examples/genia-edge-ids.class_names")
    
    from optparse import OptionParser # For using command line options
    optparser = OptionParser(description="Joachims SVM Multiclass model file processing")
    optparser.add_option("-i", "--ids", default=None, dest="ids", help="SVM feature ids")
    optparser.add_option("-m", "--model", default=None, dest="model", help="SVM model file")
    optparser.add_option("-o", "--output", default=None, dest="output", help="Output file stem")
    (options, args) = optparser.parse_args()

    #featureIds = IdSet(filename="/usr/share/biotext/GeniaChallenge/extension-data/genia/edge-examples/genia-edge-ids.feature_names")
    #model = "/usr/share/biotext/GeniaChallenge/extension-data/genia/test-set-split-McClosky-boost07/test-edge-param-opt/model-c_28000"
    #featureIds = IdSet(filename="/usr/share/biotext/GeniaChallenge/extension-data/genia/edge-examples/genia-edge-ids.feature_names")
    #model = "/usr/share/biotext/GeniaChallenge/extension-data/genia/test-set-split-McClosky-boost07/test-edge-param-opt/model-c_28000"

    
    #mapIds("a",model)
    s = getSupportVectors(options.model)
    print "vectors:", len(s)
    s = s[0:-1]
    #writeModel(s, model, "temp.txt")
    #tokenizeModel(model, "tokenized.txt")
    w = getWeights(s)
    w = assignNames(w, IdSet(filename=options.ids))
    f = open(options.output + "weights.txt", "wt")
    for pair in w:
        f.write(str(pair[0]) + "\t" + str(pair[1]) + "\n")
    f.close()
    
    d = getTokenWeights(w)
    f = open(options.output + "weights-tokens.txt", "wt")
    for pair in sorted(d.items(), key=itemgetter(1)):
        f.write(str(pair[1]) + "\t" + str(pair[0]) + "\n")
    f.close()
