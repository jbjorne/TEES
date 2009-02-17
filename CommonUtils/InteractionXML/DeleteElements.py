import sys, os, copy
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../JariSandbox/ComplexPPI/Source")
from Utils.ProgressCounter import ProgressCounter
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET
import cElementTreeUtils as ETUtils
    
def removeElements(sentence, elementName, attributes, countsByType):
    toRemove = []
    for element in sentence:
        if element.tag == elementName:
            remove = True
            for k,v in attributes.iteritems():
                if element.get(k) != v:
                    remove = False
            if remove:
                toRemove.append(element)
    for element in toRemove:
        sentence.remove(element)
        countsByType[elementName] += 1
            
# Splits entities/edges with merged types into separate elements
def processSentence(sentence, rules, countsByType):
    for key in sorted(rules.keys()):
        #print key, rules[key]
        removeElements(sentence, key, rules[key], countsByType)

def processCorpus(inputFilename, outputFilename, rules):
    print >> sys.stderr, "Loading corpus file", inputFilename
    if inputFilename.rsplit(".",1)[-1] == "gz":
        import gzip
        corpusTree = ET.parse(gzip.open(inputFilename))
    else:
        corpusTree = ET.parse(inputFilename)
    corpusRoot = corpusTree.getroot()
    
    documents = corpusRoot.findall("document")
    counter = ProgressCounter(len(documents), "Documents")
    countsByType = {}
    for k in sorted(rules.keys()):
        countsByType[k] = 0
    for document in documents:
        counter.update()
        for sentence in document.findall("sentence"):
            processSentence(sentence, rules, countsByType)
    print >> sys.stderr, "Removed"
    for k in sorted(countsByType.keys()):
        print >> sys.stderr, "  " + k + ":", countsByType[k]
    
    print >> sys.stderr, "Writing output to", options.output
    ETUtils.write(corpusRoot, options.output)

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

    # Rules e.g. "{\"pair\":{},\"interaction\":{},\"entity\":{\"isName\":\"False\"}}"
    rules = eval(options.rules)
    print >> sys.stderr, "Rules:", rules
    processCorpus(options.input, options.output, rules)
