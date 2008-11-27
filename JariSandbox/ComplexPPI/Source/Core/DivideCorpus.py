import Split
import sys
sys.path.append("..")
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET
import cElementTreeUtils as ETUtils

def getDocumentId(idString):
    return idString.rsplit(".",2)[0]

def getIdFromLine(line):
    assert(line.find("#") != -1)
    return line.split("#")[-1].strip()

if __name__=="__main__":
    from optparse import OptionParser
    optparser = OptionParser(usage="%prog [options]\n")
    optparser.add_option("-i", "--input", default=None, dest="input", help="Corpus in analysis format", metavar="FILE")
    optparser.add_option("-o", "--output", default="", dest="output", help="Output directory")
    optparser.add_option("-f", "--folds", type="int", default=10, dest="folds", help="X-fold cross validation")
    (options, args) = optparser.parse_args()

    # Load corpus and make sentence graphs
    corpusElements = SentenceGraph.loadCorpus(options.input, options.parse, options.tokenization)   
    
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

    print >> sys.stderr, "Dividing documents into folds"
    sample = Split.getFolds(len(documentIds),options.folds)
    division = {}
    for i in range(len(documentIds)): 
        division[documentIds[i]] = sample[i]

    print >> sys.stderr, "Dividing examples"
    for document in corpusElements.documents:
        sentences = document.findall("sentence")
        for sentence in sentences:
            docId = sentence.attrib["id"].rsplit(".",1)[0]
            outputTrees[division[docId]].append(sentence)
    
    for outputTree in outputTree:
        ETUtils.write
