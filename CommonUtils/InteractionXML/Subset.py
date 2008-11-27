try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET
import cElementTreeUtils as ETUtils
import random

# From Split.py, which should be moved to CommonUtils
def getSample(popSize, sampleFraction, seed=0):
    random.seed(seed)
    sample = random.sample( xrange(popSize), int(sampleFraction*float(popSize)) )
    vector = []
    for i in range(popSize):
        if i in sample:
            vector.append(0)
        else:
            vector.append(1)
    return vector

if __name__=="__main__":
    import sys
    print >> sys.stderr, "##### Create a subset of documents from an interaction XML-file #####"
    
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
    optparser = OptionParser(usage="%prog [options]\n.")
    optparser.add_option("-i", "--input", default=defaultCorpusFilename, dest="input", help="Corpus in interaction xml format", metavar="FILE")
    optparser.add_option("-o", "--output", default=defaultOutputName, dest="output", help="Output file in interaction xml format.")
    optparser.add_option("-d", "--IDs", default=None, dest="ids", help="id list in file")
    optparser.add_option("-f", "--fraction", type="float", default=1.0, dest="fraction", help="Selected set fraction")
    optparser.add_option("-s", "--seed", type="int", default=0, dest="seed", help="Seed for random set")
    optparser.add_option("-v", "--invert", default=False, dest="invert", action="store_true", help="Invert")
    (options, args) = optparser.parse_args()
    
    if options.input == None:
        print >> sys.stderr, "Error, input file not defined."
        optparser.print_help()
        sys.exit(1)
    if options.output == None:
        print >> sys.stderr, "Error, output file not defined."
        optparser.print_help()
        sys.exit(1)
    
    idList = []
    if options.ids != None:
        print >> sys.stderr, "Loading set ids from file", options.ids
        idListFile = open(options.ids)
        lines = idListFile.readlines()
        for line in lines:
            idList.append(line.strip())
            
    print >> sys.stderr, "Loading corpus file", options.input
    corpusTree = ET.parse(options.input)
    print >> sys.stderr, "Corpus file loaded"
    corpusRoot = corpusTree.getroot()

    documents = corpusRoot.findall("document")
    if options.ids == None:
        print >> sys.stderr, "No id-file, defining pseudorandom distribution"
        documentSets = getSample(len(documents), options.fraction, options.seed)

    # Remove those documents not in subset
    keptDocuments = 0
    keptSentences = 0
    removedDocuments = 0
    removedSentences = 0
    for i in range(len(documents)):
        document = documents[i]
        sentences = document.findall("sentence")
        if options.ids != None:
            keep = None
            for sentence in sentences:
                selection = sentence.attrib["origId"] in idList
                if options.invert:
                    selection = not selection
                assert(keep == None or keep == selection)
                keep = selection
            if not keep:
                corpusRoot.remove(document)
                removedDocuments += 1
                removedSentences += len(sentences)
            else:
                keptDocuments += 1
                keptSentences += len(sentences)
        else:
            selection = documentSets[i] != 0
            if options.invert:
                selection = not selection
            if selection:
                corpusRoot.remove(document)
                removedDocuments += 1
                removedSentences += len(sentences)
            else:
                keptDocuments += 1
                keptSentences += len(sentences)
    
    print >> sys.stderr, "Corpus:", keptDocuments + removedDocuments, "documents,", keptSentences + removedSentences, "sentences."
    print >> sys.stderr, "Removed:", removedDocuments, "documents,", removedSentences, "sentences."
    print >> sys.stderr, "Subset:", keptDocuments, "documents,", keptSentences, "sentences."
    
    print >> sys.stderr, "Writing subset to", options.output
    ETUtils.write(corpusRoot, options.output)
