import sys, os
from collections import defaultdict
extraPath = os.path.dirname(os.path.abspath(__file__))+"/../.."
sys.path.append(extraPath)
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET
import Utils.ElementTreeUtils as ETUtils
import re
from random import Random

def getCounts(document):
    counts = {"interactions":{}, "total":0}
    for interaction in document.getiterator("interaction"):
        iType = interaction.get("type")
        if iType not in counts:
            counts["interactions"][iType] = 0
        counts["interactions"][iType] += 1
        counts["total"] += 1

def getFractions(documents, docCounts):
    totals = {}
    for document in documents:
        counts = docCounts[document]
        for key in counts:
            if key not in totals:
                totals[key] = 0
            totals[key] += counts[key]
    total = sum(totals.values())
    fractions = {key:totals[key] / total for key in sorted(totals.keys())}
    return fractions

def stratify(input, output, oldSetNames, newSetWeights):
    print >> sys.stderr, "Loading corpus file", input
    corpusTree = ETUtils.ETFromObj(input)
    corpusRoot = corpusTree.getroot()
    
    oldSetNames = re.compile(oldSetNames)
    if isinstance(newSetWeights, basestring):
        newSetNames = eval(newSetWeights)
    sumWeights = sum(newSetWeights.values())
    newSetNames = sorted(newSetWeights.keys())
    cutoff = 0.0
    cutoffs = []
    for key in newSetNames:
        cutoffs.append((cutoff, key))
        cutoff += newSetWeights[key] / sumWeights
    
    documents = []
    for document in corpusRoot.getiterator("document"):
        if document.get("set").match(oldSetNames) != None:
            documents.append(document)
    
    random = Random(1)
    
    newSets = {x:[] for x in sorted(newSetNames.keys())}
    numDocuments = len(documents)
    for document in documents:
        cutoff = random.random()
        for j in range(1, len(cutoffs)):
            if cutoffs[j] > cutoff:
                newSets[cutoffs[j-1][1]].append(document)
                break
    print "Initial counts", {x:len(newSets[x]) for x in newSets}
    
    counts = defaultdict(int)
    for i in range(0, 100000):
        sourceSet = random.randrange(start, stop, step, _int, _maxwidth)
    
    if output != None:
        print >> sys.stderr, "Writing output to", output
        ETUtils.write(corpusRoot, output)
    return corpusTree

if __name__=="__main__":
    import sys
    print >> sys.stderr, "##### Map attributes #####"
    
    from optparse import OptionParser
    optparser = OptionParser(usage="%prog [options]\n")
    optparser.add_option("-i", "--input", default=None, help="Corpus in interaction xml format", metavar="FILE")
    optparser.add_option("-o", "--output", default=None, help="Output file in interaction xml format.")
    optparser.add_option("-s", "--sourceSets", default=None, help="dictionary of python dictionaries with attribute:value pairs.")    
    optparser.add_option("-n", "--newSets", default=None, help="dictionary of python dictionaries with attribute:value pairs.")    
    (options, args) = optparser.parse_args()
    
    if options.input == None:
        print >> sys.stderr, "Error, input file not defined."
        optparser.print_help()
        sys.exit(1)
    if options.output == None:
        print >> sys.stderr, "Error, output file not defined."
        optparser.print_help()
        sys.exit(1)

    # Rules e.g. "{'element':{'attrname':{'oldvalue':'newvalue'}}}"
    rules = eval(options.rules)
    print >> sys.stderr, "Rules:", rules
    stratify(options.input, options.output, rules)