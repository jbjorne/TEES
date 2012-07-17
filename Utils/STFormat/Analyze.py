from STTools import *

def getNestingChains(arg, chain=None):
    node = arg[1]
    if node.trigger == None: # reached protein level
        return [chain]
    else:
        if chain == None:
            chain = arg[0][0] + ":" + node.type
        else:
            chain += "-" + arg[0][0] + ":" + node.type
    chains = []
    for arg in node.arguments:
        chains.extend(getNestingChains(arg, chain))
    return chains

def analyzeNesting(documents):
    chainCounts = {}
    for doc in documents:
        argumentEvents = set()
        # Find all events that act as arguments, i.e. are not top level
        for event in doc.events:
            for arg in event.arguments:
                if arg[1].trigger != None: # event
                    argumentEvents.add(arg[1])
        # Determine nesting structures for top level events
        for event in doc.events:
            if event not in argumentEvents:
                chains = getNestingChains(("Root", event))
                for chain in chains:
                    if not chainCounts.has_key(chain):
                        chainCounts[chain] = 0
                    chainCounts[chain] += 1
    print "Counts:"
    for k in sorted(chainCounts.keys()):
        print " ", k, chainCounts[k]

if __name__=="__main__":
    from optparse import OptionParser
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"
    
    #proteins, triggers, events = load(1335418, "/home/jari/biotext/tools/TurkuEventExtractionSystem-1.0/data/evaluation-data/evaluation-tools-devel-gold")
    #write(1335418, "/home/jari/data/temp", proteins, triggers, events )
    optparser = OptionParser(description="ST format statistics")
    optparser.add_option("-i", "--input", default=None, dest="input", help="", metavar="FILE")
    (options, args) = optparser.parse_args()
    
    #p = "/home/jari/data/BioNLP09SharedTask/bionlp09_shared_task_development_data_rev1"
    #p = "/home/jari/data/BioNLP11SharedTask/BioNLP-ST_2011_Entity_Relations_development_data"
    print "Loading documents"
    documents = loadSet(options.input)
    print "Analyzing"
    analyzeNesting(documents)
    print "Statistics"
    getStatistics(documents)