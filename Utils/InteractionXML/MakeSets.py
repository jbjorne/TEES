import sys, os
import random
from collections import defaultdict
thisPath = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(thisPath,"../..")))
import Utils.ElementTreeUtils as ETUtils

def processCorpus(inPath, outPath, sourceSet, newSets, seed=1):
    print >> sys.stderr, "Loading corpus file", inPath
    corpusTree = ETUtils.ETFromObj(inPath)
    corpusRoot = corpusTree.getroot()
    
    rand = random.Random(seed)
    documents = corpusRoot.findall("document")
    counts = {"old":defaultdict(int), "new":defaultdict(int)}
    for document in documents:
        counts["old"][document.get("set")] += 1
        if sourceSet != None and document.get("set") != sourceSet:
            counts["new"][document.get("set")] += 1
            continue
        value = rand.random()
        document.set("setValue", str(value))
        document.set("origSet", document.get("set", ""))
        for setName, cutoff in newSets:
            if value <= cutoff:
                document.set("set", setName)
                break
        counts["new"][document.get("set")] += 1
    #for key in counts:
    #    counts[key] = dict(counts[key])
    print "MakeSets result:", "old=" + str(dict(counts["old"])) + ", new=" + str(dict(counts["new"]))
    if outPath != None:
        ETUtils.write(corpusRoot, outPath)
    return corpusTree

if __name__=="__main__":
    from optparse import OptionParser
    optparser = OptionParser(usage="%prog [options]\n")
    optparser.add_option("-i", "--input", default=None, help="Corpus in interaction xml format", metavar="FILE")
    optparser.add_option("-o", "--output", default=None, help="Output file in interaction xml format.")
    optparser.add_option("-r", "--source", default=None)
    optparser.add_option("-s", "--sets", default=None)
    optparser.add_option("-d", "--seed", type=int, default=1)
    optparser.add_option("-c", "--cutoffs", default=None)
    (options, args) = optparser.parse_args()
    
    sets = options.sets.split(",")
    cutoffs = [float(x) for x in options.cutoffs.split(",")]
    assert len(sets) == len(cutoffs)
    sets = [(x, y) for x, y in zip(sets, cutoffs)]
    processCorpus(options.input, options.output, options.source, sets)
