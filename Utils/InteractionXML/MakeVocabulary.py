import sys, os
extraPath = os.path.dirname(os.path.abspath(__file__))+"/../.."
sys.path.append(extraPath)
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET
import Utils.ElementTreeUtils as ETUtils
import Utils.InteractionXML.InteractionXMLUtils as IXMLUtils
from Utils.Libraries.wvlib_light.lwvlib import WV
from Utils.ProgressCounter import ProgressCounter
import gzip, json
from collections import defaultdict
    
def removeAttributes(parent, elementName, attributes, countsByType):
    for element in parent.getchildren():
        if element.tag == elementName:
            for attribute in attributes:
                if element.get(attribute) != None:
                    del element.attrib[attribute]
                    countsByType[elementName + ":" + attribute] += 1
        removeAttributes(element, elementName, attributes, countsByType)

def processCorpus(input, output, wordVectorPath, tokenizerName="McCC"):
    print >> sys.stderr, "Making vocabulary"
    print >> sys.stderr, "Loading corpus file", input
    corpusTree = ETUtils.ETFromObj(input)
    corpusRoot = corpusTree.getroot()
    
    print >> sys.stderr, "Loading word vectors from", wordVectorPath
    wv = WV.load(wordVectorPath, 100000, 10000000)
    
    documents = corpusRoot.findall("document")
    counter = ProgressCounter(len(documents), "Documents")
    counts = defaultdict(int)
    vocabulary = {}
    for document in documents:
        counter.update()
        counts["document"] += 1
        for sentence in document.findall("sentence"):
            counts["sentence"] += 1
            tokenization = IXMLUtils.getTokenizationElement(sentence, tokenizerName)
            if tokenization != None:
                counts["tokenization"] += 1
                for token in tokenization.findall(token):
                    counts["token"] += 1
                    text = token.get("text")
                    if text not in vocabulary:
                        counts["token-unique"] += 1
                        vector = wv.w_to_normv(token.get("text").lower())
                        if vector != None:
                            counts["vector"] += 1
                            vector = vector.tolist()
                        else:
                            counts["no-vector"] += 1
                        vocabulary[text] = vector              
    
    #for k in sorted(countsByType.keys()):
    #    print >> sys.stderr, "  " + k + ":", countsByType[k]
    
    if output != None:
        print >> sys.stderr, "Writing output to", output
        with gzip.open(output) as f:
            json.dump(vocabulary, f)
    return vocabulary

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
    optparser.add_option("-o", "--output", default=None, dest="output", help="Output file in interaction xml format.")
    optparser.add_option("-w", "--wordvectors", default=None, dest="wordvectors", help="dictionary of python dictionaries with attribute:value pairs.")    
    (options, args) = optparser.parse_args()
    
    if options.input == None:
        print >> sys.stderr, "Error, input file not defined."
        optparser.print_help()
        sys.exit(1)
    if options.output == None:
        print >> sys.stderr, "Error, output file not defined."
        optparser.print_help()
        sys.exit(1)

    # Rules e.g. "{\"pair\":{},\"interaction\":{},\"entity\":{\"given\":\"False\"}}"
    processCorpus(options.input, options.output, options.wordvectors)
