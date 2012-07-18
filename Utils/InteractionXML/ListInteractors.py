import sys, os
extraPath = os.path.dirname(os.path.abspath(__file__))+"/../.."
#IF LOCAL
extraPath = os.path.dirname(os.path.abspath(__file__))+"/../../JariSandbox/ComplexPPI/Source"
#ENDIF
sys.path.append(extraPath)
from Utils.ProgressCounter import ProgressCounter
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET
import Utils.ElementTreeUtils as ETUtils

def processCorpus(input, attrs=["text"]):
    print attrs
    print >> sys.stderr, "Loading corpus file", input
    corpusRoot = ETUtils.ETFromObj(input).getroot()
    
    documents = corpusRoot.findall("document")
    counter = ProgressCounter(len(documents), "Documents")
    countsByType = {}
    interactors = {}
    for document in documents:
        entDict = {}
        for entity in document.getiterator("entity"):
            entDict[entity.get("id")] = entity
        for interaction in document.getiterator("interaction"):
            e1 = entDict[interaction.get("e1")]
            e2 = entDict[interaction.get("e2")]
            # form identifier tuples
            e1Tuple = []
            for attr in attrs: e1Tuple.append(e1.get(attr))
            e1Tuple = tuple(e1Tuple)
            e2Tuple = []
            for attr in attrs: e2Tuple.append(e2.get(attr))
            e2Tuple = tuple(e2Tuple)
            interactors = [e1Tuple, e2Tuple]
            #interactors.sort()
            print interactors
            # add interactors
#            if not interactors.has_key(e1):
#                interactors[e1] = set()
#            if not interactors.has_key(e2):
#                interactors[e2] = set()
#            interactors[e1].add(e2)
#            interactors[e2].add(e1)

if __name__=="__main__":
    import sys
    print >> sys.stderr, "##### Split elements with merged types #####"
    
    from optparse import OptionParser
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"

    optparser = OptionParser(usage="%prog [options]\nPath generator.")
    optparser.add_option("-i", "--input", default=None, dest="input", help="Corpus in interaction xml format", metavar="FILE")
    optparser.add_option("-a", "--attr", default=None, dest="attr", help="Output file in interaction xml format.")
    (options, args) = optparser.parse_args()
    
    if options.input == None:
        print >> sys.stderr, "Error, input file not defined."
        optparser.print_help()
        sys.exit(1)

    processCorpus(options.input, eval(options.attr))
