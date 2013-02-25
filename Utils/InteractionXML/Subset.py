import sys, os
thisPath = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(thisPath,"../..")))
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET
import Utils.ElementTreeUtils as ETUtils
import random
from collections import defaultdict
import types

def getElementCounts(filename, elementTags=[]):
    if filename.endswith(".gz"):
        f = gzip.open(filename, "rt")
    else:
        f = open(filename, "rt")
    counts = defaultdict(int)
    for line in f:
        for elementTag in elementTags:
            if "<" + elementTag in line:
                counts[elementTag] += 1
    f.close()
    return counts

# From Split.py, which should be moved to CommonUtils
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

def selectByAttributes(element, attributes):
    for key in attributes:
        if element.get(key) in attributes[key]:
            return True
    return False

def select(elementCount, documentSets, element, ids, attributes, invert):
    if ids == None and attributes == None:
        selected = documentSets[elementCount] != 0
    else:
        selected = True
        if ids != None:
            selected = selected and element.get("id") in ids
        if attributes != None:
            selected = selected and selectByAttributes(element, attributes)
        selected = not selected
    if invert:
        selected = not selected
    return selected

def getSubset(input, output=None, fraction=1.0, seed=0, ids=None, attributes=None, invert=False, targetElementTag="document"): 
    distribution = None
    if ids == None and attributes == None:
        print >> sys.stderr, "No id-file, using pseudorandom distribution"
        distribution = getSample(getElementCounts(input, [targetElementTag])[targetElementTag], fraction, seed)
    elif attributes != None:
        print >> sys.stderr, "Selecting subset with attributes:", attributes
        for key in attributes:
            assert type(attributes[key]) in (types.ListType, types.TupleType), attributes

    counts = defaultdict(int)
    
    outWriter = None
    if output != None:
        outWriter = ETUtils.ETWriter(output)
    targetElementCount = 0
    skip = False
    for event in ETUtils.ETIteratorFromObj(input, ("start", "end")):
        if event[0] == "start":
            if event[1].tag == targetElementTag:
                skip = select(targetElementCount, distribution, event[1], ids, attributes,invert)
                targetElementCount += 1
            if not skip:
                outWriter.begin(event[1])
                counts[event[1].tag + ":kept"] += 1
            else:
                counts[event[1].tag + ":removed"] += 1
        elif event[0] == "end":
            if not skip:
                outWriter.end(event[1])
            if event[1].tag == targetElementTag:
                skip = False
    if output != None:
        outWriter.close()
        ETUtils.encodeNewlines(output)
    
    print >> sys.stderr, "Subset for " + str(input) + ": " + str(counts)

if __name__=="__main__":
    import sys
    print >> sys.stderr, "##### Create a subset of documents from an interaction XML-file #####"
    
    from optparse import OptionParser
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"

    optparser = OptionParser(usage="%prog [options]\n.")
    optparser.add_option("-i", "--input", default=None, dest="input", help="Corpus in interaction xml format", metavar="FILE")
    optparser.add_option("-o", "--output", default=None, dest="output", help="Output file in interaction xml format.")
    optparser.add_option("-d", "--IDs", default=None, dest="ids", help="id list in file")
    optparser.add_option("-f", "--fraction", type="float", default=1.0, dest="fraction", help="Selected set fraction")
    optparser.add_option("-s", "--seed", type="int", default=0, dest="seed", help="Seed for random set")
    optparser.add_option("-v", "--invert", default=False, dest="invert", action="store_true", help="Invert")
    optparser.add_option("-a", "--attributes", default=None, dest="attributes", help="Attributes")
    (options, args) = optparser.parse_args()
    
    if options.input == None:
        print >> sys.stderr, "Error, input file not defined."
        optparser.print_help()
        sys.exit(1)
    
    idList = None
    if options.ids != None:
        idList = []
        print >> sys.stderr, "Loading set ids from file", options.ids
        idListFile = open(options.ids)
        lines = idListFile.readlines()
        for line in lines:
            idList.append(line.strip())
        idList = set(idList)
    
    if options.attributes != None:
        options.attributes = eval(options.attributes)
    
    getSubset(options.input, options.output, options.fraction, options.seed, idList, options.attributes, options.invert)