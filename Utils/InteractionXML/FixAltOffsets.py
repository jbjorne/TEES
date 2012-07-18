__version__ = "$Revision: 1.1 $"

import sys,os
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET
import Utils.ElementTreeUtils as ETUtils
import Utils.Range as Range

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/..")
from Utils.ProgressCounter import ProgressCounter

def fixAltOffsets(input, output=None):
    print >> sys.stderr, "Loading corpus", input
    corpusTree = ETUtils.ETFromObj(input)
    print >> sys.stderr, "Corpus file loaded"
    corpusRoot = corpusTree.getroot()
    
    docCount = 0
    sentencesCreated = 0
    sentences = [x for x in corpusRoot.getiterator("sentence")]
    counter = ProgressCounter(len(sentences), "FixAltOffsets")
    fixCount = 0
    # fix spans
    for sentence in sentences:
        counter.update(1, "Fixing AltOffsets for sentence ("+sentence.get("id")+"): ")
        sentOffset = Range.charOffsetToSingleTuple(sentence.get("charOffset"))
        for entity in sentence.findall("entity"):
            altOffsetString = entity.get("altOffset")
            if altOffsetString == None:
                continue
            #print altOffsetString
            altOffsets = Range.charOffsetToTuples(altOffsetString)
            assert len(altOffsets) == 1
            for i in range(len(altOffsets)):
                altOffset = altOffsets[i] 
                altOffsets[i] = (altOffset[0] - sentOffset[0], altOffset[1] - sentOffset[0])
            entity.set("altOffset", Range.tuplesToCharOffset(altOffsets))
            fixCount += 1
        
    print >> sys.stderr, "Fixed", fixCount, "altOffsets"
        
    if output != None:
        print >> sys.stderr, "Writing output to", output
        ETUtils.write(corpusRoot, output)
    return corpusTree
    
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

    optparser = OptionParser(usage="%prog [options]\n")
    optparser.add_option("-i", "--input", default=None, dest="input", help="Corpus in interaction xml format", metavar="FILE")
    optparser.add_option("-o", "--output", default=None, dest="output", help="Output file in interaction xml format.")
    (options, args) = optparser.parse_args()
    
    makeSentences(input=options.input, output=options.output)
    