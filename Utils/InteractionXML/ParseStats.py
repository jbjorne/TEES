try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET
import Utils.ElementTreeUtils as ETUtils
import sys
import CorpusElements
from optparse import OptionParser
from collections import defaultdict

def parseStats(input):
    print >> sys.stderr, "Loading input file", input
    inputTree = ETUtils.ETFromObj(input)
    inputRoot = inputTree.getroot()
    counts = defaultdict(int)
    for sentence in inputRoot.getiterator("sentence"):
        counts["sentence"] += 1
        analysesElement = sentence.find("sentenceanalyses")
        if analysesElement == None:
            counts["sentence-no-analyses"] += 1
            continue
        # Create parses element (if needed)
        parsesElement = analysesElement.find("parses")
        if parsesElement == None:
            counts["sentence-no-parses"] += 1
            continue
        # Loop through parses
        for parseElement in parsesElement:
            parserName = parseElement.get("parser")
            counts["parse:"+parserName] += 1
            if parseElement.get("pennstring") in ["", None]:
                counts["parse:"+parserName+"(no penn)"] += 1
            if len(parseElement.findall("dependency")) == 0:
                counts["parse:"+parserName+"(no dependencies)"] += 1
            if len(parseElement.findall("phrase")) == 0:
                counts["parse:"+parserName+"(no phrases)"] += 1
        # Tokenizations
        tokenizationsElement = analysesElement.find("tokenizations")
        if tokenizationsElement == None:
            counts["sentence-no-tokenizations"] += 1
            continue
        # Loop through tokenizations
        for tokenizationElement in tokenizationsElement:
            tokenizerName = tokenizationElement.get("tokenizer")
            counts["tokenization:"+tokenizerName] += 1
            if len(tokenizationElement.findall("token")) == 0:
                counts["tokenization:"+tokenizerName+"(no tokens)"] += 1
    
    print >> sys.stderr, "Parse statistics for", input
    for key in sorted(counts.keys()):
        print >> sys.stderr, " ", key + ":", counts[key]
        
if __name__=="__main__":
    print >> sys.stderr, "##### Parse Statistics #####"
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"

    optparser = OptionParser(usage="%prog [options]\nCreate an html visualization for a corpus.")
    optparser.add_option("-i", "--input", default=None, dest="input", help="Corpus in analysis format", metavar="FILE")
    (options, args) = optparser.parse_args()
    assert(options.input != None)
    parseStats(options.input)