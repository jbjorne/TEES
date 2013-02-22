import types
from collections import defaultdict
from STTools import *

def getCounts(documents):
    counts = defaultdict(int)
    counts["modifier"] = 0
    counts["modifier(spec)"] = 0
    counts["modifier(neg)"] = 0
    for doc in documents:
        if doc.proteins != None:
            for protein in doc.proteins: 
                counts["protein("+protein.type+")"] += 1
                counts["protein"] += 1
        if doc.triggers != None:
            for trigger in doc.triggers: 
                counts["trigger("+trigger.type+")"] += 1
                counts["trigger"] += 1
        if doc.events != None:
            for event in doc.events:
                if event.trigger != None:
                    counts["event("+event.type+")"] += 1
                    counts["event"] += 1
                else:
                    counts["relation("+event.type+")"] += 1
                    counts["relation"] += 1
                if event.speculation != None:
                    counts["modifier"] += 1
                    counts["modifier(spec)"] += 1
                if event.negation != None:
                    counts["modifier"] += 1
                    counts["modifier(neg)"] += 1
        for ann in doc.events:
            for arg in ann.arguments:
                counts["arg("+arg.type+")"] += 1
                counts["arg"] += 1
    return counts

def getSet(setPath, setName, a2Tags):
    if type(a2Tags) in types.StringTypes:
        a2Tags = a2Tags.split(",")
    print "Loading set " + setName + ":", setPath
    if a2Tags != None:
        return loadSet(setPath, a2Tags=a2Tags)
    else:
        return loadSet(setPath)

def compare(a, b, a2Tags=None):
    print >> sys.stderr, "Comparing BioNLP Shared Task format document sets"
    docsA = getSet(a, "A", a2Tags)
    docsB = getSet(b, "B", a2Tags)
    countsA = getCounts(docsA)
    countsB = getCounts(docsB)
    allKeys = list(set(countsA.keys() + countsB.keys()))
    allKeys.sort()
    maxKeyLength = max([len(x) for x in allKeys])
    # Sets
    print "Sets"
    print "A:", a, "(documents: " + str(len(docsA)) + ")"
    print "B:", b, "(documents: " + str(len(docsB)) + ")"
    # Make title
    titleLine = "Category"
    while len(titleLine) <= maxKeyLength:
        titleLine += " "
    titleLine += "A"
    titleLine += " " * 9
    titleLine += "B"
    titleLine += " " * 9
    titleLine += "Diff"
    titleLine += " " * 6
    titleLine += "Status"
    print titleLine
    # Make lines
    for key in allKeys:
        line = key
        while len(line) <= maxKeyLength:
            line += " "
        valA = (countsA[key] / float(len(docsA)))
        line += "%.2f" % valA
        while len(line) <= maxKeyLength + 10:
            line += " "
        valB = (countsB[key] / float(len(docsB)))
        line += "%.2f" % valB
        # Diff
        while len(line) <= maxKeyLength + 20:
            line += " "
        if valA == 0 or valB == 0:
            diff = None
            line += "N/A"
        else:
            diff = valA / valB
            line += "%.2f" % diff
        # Dist
        while len(line) <= maxKeyLength + 30:
            line += " "
        if diff != None:
            dist = abs(1.0 - diff)
            maxCount = 30
            step = 0.01
            count = 0
            while dist > 0:
                dist -= step
                count += 1
                line += "!"
                if count >= maxCount:
                    line += "+"
                    break
        else:
            line += "-"
        #if dist > 0.05:
        #    line += "!!!!!!!!!!+"
        #else:
        #    for i in range(int(dist * 100 * 2)):
        #        line += "!"
        print line

if __name__=="__main__":
    import sys
    
    from optparse import OptionParser
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"

    optparser = OptionParser(description="Compare event distribution")
    optparser.add_option("-a", "--inputA", default=None, dest="inputA", help="", metavar="FILE")
    optparser.add_option("-b", "--inputB", default=None, dest="inputB", help="")
    optparser.add_option("-t", "--a2Tags", default=None, dest="a2Tags", help="")
    #optparser.add_option("-p", "--parse", default=None, dest="parse", help="Name of parse element.")
    (options, args) = optparser.parse_args()
    
    compare(options.inputA, options.inputB, a2Tags=options.a2Tags)