import cElementTreeUtils as ETUtils
import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/..")
import Core.SentenceGraph as SentenceGraph

if __name__=="__main__":
    import sys
    print >> sys.stderr, "##### Calculating entity head token offsets #####"
    
    from optparse import OptionParser
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"

    optparser = OptionParser(usage="%prog [options]\nRecalculate head token offsets.")
    optparser.add_option("-i", "--input", default=None, dest="input", help="Corpus in interaction xml format", metavar="FILE")
    optparser.add_option("-o", "--output", default=None, dest="output", help="Output file in interaction xml format.")
    optparser.add_option("-t", "--tokenization", default=None, dest="tokenization", help="Tokenization element name for calculating head offsets")
    optparser.add_option("-p", "--parse", default=None, dest="parse", help="Parse element name for calculating head offsets")
    (options, args) = optparser.parse_args()
    
    print >> sys.stderr, "Removing existing head offsets"
    removeCount = 0
    xml = ETUtils.ETFromObj(options.input)
    for d in xml.getroot().findall("document"):
        for s in d.findall("sentence"):
            for e in s.findall("entity"):
                if e.get("headOffset") != None:
                    removeCount += 1
                    del e.attrib["headOffset"]
    print >> sys.stderr, "Removed head offsets from", removeCount, "entities"
    
    # SentenceGraph automatically calculates head offsets and adds them to entities if they are missing
    corpusElements = SentenceGraph.loadCorpus(options.input, options.parse, options.tokenization)
    print >> sys.stderr, "Writing output to", options.output
    ETUtils.write(corpusElements.rootElement, options.output)