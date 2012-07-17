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
                counts["event("+event.type+")"] += 1
                counts["event"] += 1
                if event.speculation != None:
                    counts["modifier"] += 1
                    counts["modifier(spec)"] += 1
                if event.negation != None:
                    counts["modifier"] += 1
                    counts["modifier(neg)"] += 1
        if doc.relations != None:
            for relation in doc.relations: 
                counts["relation("+relation.type+")"] += 1
                counts["relation"] += 1
        for ann in doc.events + doc.relations:
            for arg in ann.arguments:
                counts["arg("+arg[0]+")"] += 1
                counts["arg"] += 1
    return counts

def compare(a, b, a2Tag="a2"):
    print >> sys.stderr, "Comparing BioNLP Shared Task format document sets"
    print "Loading set A:", a
    docsA = loadSet(a, a2Tag=a2Tag)
    print "Loading set B:", b
    docsB = loadSet(b, a2Tag=a2Tag)
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
    optparser.add_option("-t", "--a2Tag", default="a2", dest="a2Tag", help="")
    #optparser.add_option("-p", "--parse", default=None, dest="parse", help="Name of parse element.")
    (options, args) = optparser.parse_args()
    
    compare(options.inputA, options.inputB, a2Tag=options.a2Tag)