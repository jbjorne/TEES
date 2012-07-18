try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET
import Utils.ElementTreeUtils as ETUtils
import sys
import CorpusElements
from optparse import OptionParser

if __name__=="__main__":
    print >> sys.stderr, "##### Compare Parse #####"
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"

    optparser = OptionParser(usage="%prog [options]\nCreate an html visualization for a corpus.")
    #optparser.add_option("-i", "--input", default=None, dest="input", help="Corpus in analysis format", metavar="FILE")
    optparser.add_option("-s", "--source", default=None, dest="source", help="Corpus in analysis format", metavar="FILE")
    optparser.add_option("-r", "--target", default=None, dest="target", help="Corpus in analysis format", metavar="FILE")
    #optparser.add_option("-o", "--output", default=None, dest="output", help="Corpus in analysis format", metavar="FILE")
    optparser.add_option("-t", "--tokenization", default="split-McClosky", dest="tokenization", help="Tokenization element name")
    optparser.add_option("-p", "--parse", default="split-McClosky", dest="parse", help="Parse element name")
    (options, args) = optparser.parse_args()
    assert(options.source != None)
    assert(options.target != None)
    #assert(options.output != None)
    
    print >> sys.stderr, "Loading source:",
    sourceElements = CorpusElements.loadCorpus(options.source, options.parse, options.tokenization)
    print >> sys.stderr, "Loading target:",
    targetElements = CorpusElements.loadCorpus(options.target, options.parse, options.tokenization)
    parseCopied = None
    tokenizationCopied = None
    print >> sys.stderr, "Mapping sentences"
    origIdToSentences = {}
    for sourceSentence in sourceElements.sentences:
        origIdToSentences[sourceSentence.sentence.get("origId")] = [sourceSentence, None]
    for targetSentence in targetElements.sentences:
        assert origIdToSentences.has_key(targetSentence.sentence.get("origId")), targetSentence.sentence.get("origId")
        origIdToSentences[targetSentence.sentence.get("origId")][1] = targetSentence
    print >> sys.stderr, "Comparing sentences"
    count = 0
    for key in sorted(origIdToSentences.keys()):
        sourceSentence = origIdToSentences[key][0]
        targetSentence = origIdToSentences[key][1]
        #for sourceSentence, targetSentence in zip(sourceElements.sentences, targetElements.sentences):
        assert sourceSentence.sentence.get("origId") == targetSentence.sentence.get("origId"), (sourceSentence.sentence.get("origId"), targetSentence.sentence.get("origId"))
        sId = sourceSentence.sentence.get("origId")
        for sourceToken, targetToken in zip(sourceSentence.tokens, targetSentence.tokens):
            if sourceToken.attrib != targetToken.attrib:
                print >> sys.stderr, sId + ": tok diff " + sourceToken.get("id") + "/" + targetToken.get("id")
        for sourceDep, targetDep in zip(sourceSentence.dependencies, targetSentence.dependencies):
            if sourceDep.attrib != targetDep.attrib:
                print >> sys.stderr, sId + ": dep diff " + sourceDep.get("id") + "/" + targetDep.get("id")
        count += 1
    print >> sys.stderr, "Done, compared", count, "sentences"