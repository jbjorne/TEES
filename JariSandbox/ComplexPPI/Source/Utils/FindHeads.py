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

    defaultCorpusFilename = "BioInfer.xml"
    defaultOutputName = "BioInfer.xml"
    optparser = OptionParser(usage="%prog [options]\nPath generator.")
    optparser.add_option("-i", "--input", default=defaultCorpusFilename, dest="input", help="Corpus in interaction xml format", metavar="FILE")
    optparser.add_option("-o", "--output", default=defaultOutputName, dest="output", help="Output file in interaction xml format.")
    optparser.add_option("-t", "--tokenization", default=None, dest="tokenization", help="Tokenization element name")
    optparser.add_option("-p", "--parse", default=None, dest="parse", help="Parse element name")
    (options, args) = optparser.parse_args()

    corpusElements = SentenceGraph.loadCorpus(options.input, options.parse, options.tokenization)
    print >> sys.stderr, "Writing output to", options.output
    ETUtils.write(corpusElements.rootElement, options.output)