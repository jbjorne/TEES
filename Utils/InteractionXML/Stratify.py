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
    counts = {}
    for interaction in document.getiterator("interaction"):
        iType = interaction.get("type")
        if iType not in counts:
            counts[iType] = 0
        counts[iType] += 1
    return counts

def getTotals(documents, docCounts):
    totals = {}
    for document in documents:
        counts = docCounts[document]
        for key in counts:
            if key not in totals:
                totals[key] = 0
            totals[key] += counts[key]
    return totals

def getFractions(totals):
    total = float(sum(totals.values()))
    fractions = {key:totals[key] / total for key in sorted(totals.keys())}
    return fractions

def getDistance(fractionsA, fractionsB, allKeys):
    distances = []
    for key in allKeys:
        distances.append(abs(fractionsA[key] - fractionsB[key]))
    return sum(distances) / len(distances)

def stratify(input, output, oldSetNames, newSetWeights):
    print >> sys.stderr, "##### Stratify Sets #####"
    print >> sys.stderr, "Loading corpus file", input
    corpusTree = ETUtils.ETFromObj(input)
    corpusRoot = corpusTree.getroot()
    
    oldSetNames = re.compile(oldSetNames)
    if isinstance(newSetWeights, basestring):
        newSetWeights = eval(newSetWeights)
    sumWeights = sum(newSetWeights.values())
    newSetNames = sorted(newSetWeights.keys())
    cutoff = 0.0
    cutoffs = []
    for key in newSetNames:
        cutoff += newSetWeights[key] / sumWeights
        cutoffs.append({"cutoff":cutoff, "name":key})
    print >> sys.stderr, "Cutoffs", cutoffs
    
    documents = []
    numDocs = 0
    for document in corpusRoot.getiterator("document"):
        numDocs += 1
        if oldSetNames.match(document.get("set")) != None:
            documents.append(document)
    print >> sys.stderr, "Matching documents", len(documents), "/", numDocs
    docCounts = {}
    for document in documents:
        docCounts[document] = getCounts(document)
    
    random = Random(1)
    
    newSets = {x:[] for x in newSetNames}
    for document in documents:
        cutoff = random.random()
        for i in range(len(cutoffs)):
            if cutoff <= cutoffs[i]["cutoff"]:
                newSets[cutoffs[i]["name"]].append(document)
                break
            if i == len(cutoffs) - 1:
                raise Exception("No set " + str(cutoff))
    print "Initial document counts", {x:len(newSets[x]) for x in newSets}
    fullFractions = getFractions(getTotals(documents, docCounts))
    print "Full fractions", fullFractions
    allKeys = sorted(fullFractions.keys())
    setTotals = {x:getTotals(newSets[x], docCounts) for x in newSetNames}
    print "Initial set totals", setTotals
    setFractions = {x:getFractions(setTotals[x]) for x in newSetNames}
    print "Initial set fractions", setFractions
    setDistances = {}
    for i in range(len(newSetNames) - 1):
        for j in range(i + 1, len(newSetNames)):
            a = newSetNames[i]
            b = newSetNames[j]
            distanceA = getDistance(setFractions[a], fullFractions, allKeys)
            distanceB = getDistance(setFractions[b], fullFractions, allKeys)
            avgDistance = 0.5 * (distanceA + distanceB)
            if a > b:
                a, b = b, a
            if a not in setDistances:
                setDistances[a] = {}
            setDistances[a][b] = avgDistance
    print "Initial distances", setDistances
    
    counts = defaultdict(int)
    for i in range(0, 100000):
        random.shuffle(newSetNames)
        a = newSetNames[0]
        b = newSetNames[1]
        if a > b:
            a, b = b, a
        setA = newSets[a]
        setB = newSets[b]
        docA = setA[random.randrange(0, len(setA))]
        docB = setB[random.randrange(0, len(setB))]
        if len(docCounts[docA]) == 0 and len(docCounts[docB]) == 0:
            counts["empty-pair"] += 1
            continue 
        newTotalsA = {x:setTotals[a].get(x, 0) - docCounts[docA].get(x, 0) + docCounts[docB].get(x, 0) for x in allKeys}
        newTotalsB = {x:setTotals[b].get(x, 0) + docCounts[docA].get(x, 0) - docCounts[docB].get(x, 0) for x in allKeys}
        newFractionsA = getFractions(newTotalsA)
        newFractionsB = getFractions(newTotalsB)
        distanceA = getDistance(newFractionsA, fullFractions, allKeys)
        distanceB = getDistance(newFractionsB, fullFractions, allKeys)
        avgDistance = 0.5 * (distanceA + distanceB)
        if setDistances[a][b] > avgDistance:
            setTotals[a] = newTotalsA
            setTotals[b] = newTotalsB
            setDistances[a][b] = avgDistance
            setA.remove(docA)
            setB.remove(docB)
            setA.append(docB)
            setB.append(docA)
            counts["swaps"] += 1
            counts["last-swap-round"] = i
        counts["rounds"] += 1
    
    print dict(counts)
    print "New document counts", {x:len(newSets[x]) for x in newSets}
    print "New totals", setTotals
    print "New fractions", {x:getFractions(setTotals[x]) for x in newSetNames}
    print "New distances", setDistances
    
    for newSetName in newSetNames:
        for document in newSets[newSetName]:
            document.set("set", newSetName)
    
    if output != None:
        print >> sys.stderr, "Writing output to", output
        ETUtils.write(corpusRoot, output)
    return corpusTree

if __name__=="__main__":
    from optparse import OptionParser
    optparser = OptionParser(usage="%prog [options]\n")
    optparser.add_option("-i", "--input", default=None, help="Corpus in interaction xml format", metavar="FILE")
    optparser.add_option("-o", "--output", default=None, help="Output file in interaction xml format.")
    optparser.add_option("-s", "--sourceSets", default=None, help="")    
    optparser.add_option("-n", "--newSets", default=None, help="")    
    (options, args) = optparser.parse_args()

    stratify(options.input, options.output, options.sourceSets, options.newSets)