import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/..")
from Core.IdSet import IdSet
import Core.ExampleUtils as ExampleUtils
from Utils.ProgressCounter import ProgressCounter

def readWeights(weightFile, cutoff=10.0):
    weightFeatures = []
    f = open(weightFile, "rt")
    for line in f.readlines():
        weight, feature = line.split()
        weight = float(weight)
        if weight > cutoff:
            feature = feature.strip()
            weightFeatures.append(feature)
    f.close()
    weightFeatures.sort()
    print "Weight features:", len(weightFeatures)
    return weightFeatures

def polynomizeExamples(exampleFile, outFile, weightFeatures, idSet):
    outFile = open(outFile, "wt")
    addCount = 0
    
    f = open(exampleFile)
    numExamples = sum([1 for line in f])
    f.close()
    counter = ProgressCounter(numExamples, "Polynomize examples", step=0)
    
    weightFeatureIds = {}
    for weightFeature in weightFeatures:
        wId = idSet.getId(weightFeature, False)
        if wId == None:
            sys.exit("Weight vector feature", weightFeature, "not in id file")
        weightFeatureIds[weightFeature] = wId
    
    print "Polynomizing", exampleFile
    exampleCache = []
    for example in ExampleUtils.readExamples(exampleFile):
        counter.update(1, "Processing example ("+example[0]+"): ")
        features = example[2]
        for i in range(len(weightFeatures)-1):
            wI = weightFeatures[i]
            wIid = weightFeatureIds[wI]
            if not features.has_key(wIid):
                continue
            for j in range(i + 1, len(weightFeatures)):
                wJ = weightFeatures[j]
                wJid = weightFeatureIds[wJ]
                if not features.has_key(wJid):
                    continue
                # Make polynomial feature
                features[idSet.getId(wI + "_AND_" + wJ)] = 1
                addCount += 1
        exampleCache.append(example)
        if len(exampleCache) > 50:
            ExampleUtils.appendExamples(exampleCache, outFile)
            exampleCache = []
    ExampleUtils.appendExamples(exampleCache, outFile)
    outFile.close()
    print "Added", addCount, "polynomial features"

if __name__=="__main__":
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"
        
    from optparse import OptionParser # For using command line options
    optparser = OptionParser()
    optparser.add_option("-i", "--ids", default=None, dest="ids", help="")
    optparser.add_option("-e", "--examples", default=None, dest="examples", help="")
    optparser.add_option("-j", "--idOutput", default=None, dest="idOutput", help="")
    optparser.add_option("-o", "--output", default=None, dest="output", help="")
    optparser.add_option("-w", "--weights", default=None, dest="weights", help="")
    optparser.add_option("-c", "--cutoff", type="float", default=10.0, dest="cutoff", help="")
    (options, args) = optparser.parse_args()

    #classIds = IdSet(filename="/usr/share/biotext/GeniaChallenge/extension-data/genia/edge-examples/genia-edge-ids.class_names")
    featureIds = IdSet(filename=options.ids)
    weightFeatures = readWeights(options.weights, options.cutoff)
    polynomizeExamples(options.examples, options.output, weightFeatures, featureIds)
    featureIds.write(options.idOutput)
