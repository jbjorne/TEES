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
    for document in corpusRoot.findall("document"):
        for sentence in corpusRoot.findall("sentence"):
            tokenization = IXMLUtils.getTokenizationElement(sentence, tokenizerName)
            for token in tokenization.findall(token):
                vector = wv.w_to_normv(token.get("text").lower())
    
    #for k in sorted(countsByType.keys()):
    #    print >> sys.stderr, "  " + k + ":", countsByType[k]
    
    if output != None:
        print >> sys.stderr, "Writing output to", output
        ETUtils.write(corpusRoot, output)
    return corpusTree

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
    optparser.add_option("-r", "--rules", default=None, dest="rules", help="dictionary of python dictionaries with attribute:value pairs.")    
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
    rules = eval(options.rules)
    print >> sys.stderr, "Rules:", rules
    processCorpus(options.input, options.output, rules)
