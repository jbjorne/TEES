"""
Pseudorandomly distributed subsets
"""
__version__ = "$Revision: 1.3 $"

import Split
import sys, os
sys.path.append("..")
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET
import Utils.ElementTreeUtils as ETUtils
import Utils.InteractionXML.CorpusElements as CorpusElements

if __name__=="__main__":
    from optparse import OptionParser
    optparser = OptionParser(usage="%prog [options]\n")
    optparser.add_option("-i", "--input", default=None, dest="input", help="Corpus in analysis format", metavar="FILE")
    optparser.add_option("-o", "--output", default=None, dest="output", help="Output directory")
    optparser.add_option("-f", "--folds", type="int", default=10, dest="folds", help="X-fold cross validation")
    (options, args) = optparser.parse_args()

    # Load corpus and make sentence graphs
    corpusElements = CorpusElements.loadCorpus(options.input)   
    
    outputTrees = []
    for i in range(options.folds):
        newRoot = ET.Element("corpus")
        for key in corpusElements.rootElement.attrib.keys():
            newRoot.attrib[key] = corpusElements.rootElement.attrib[key]
        outputTrees.append(newRoot)
    
    print >> sys.stderr, "Reading document ids"
    documentIds = []
    for document in corpusElements.documents:
        docId = document.attrib["id"]
        assert( not docId in documentIds )
        documentIds.append(docId)

    print >> sys.stderr, "Calculating document division"
    sample = Split.getFolds(len(documentIds),options.folds)
    division = {}
    for i in range(len(documentIds)): 
        division[documentIds[i]] = sample[i]

    print >> sys.stderr, "Dividing documents"
    for document in corpusElements.documents:
        docId = document.attrib["id"]
        outputTrees[division[docId]].append(document)
    
    for i in range(options.folds):
        if options.output == None:
            filename = options.input + ".fold" + str(i)
        else:
            filename = os.path.join(options.output, os.path.basename(options.input) + ".fold" + str(i))
        print >> sys.stderr, "Writing file", filename
        ETUtils.write(outputTrees[i], filename)
