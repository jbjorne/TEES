try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET
import Utils.ElementTreeUtils as ETUtils
import sys
import CorpusElements
from optparse import OptionParser

def copyParse(input, source, output, parse, tokenization):
    print >> sys.stderr, "Loading input file", input
    inputTree = ETUtils.ETFromObj(input)
    inputRoot = inputTree.getroot()
    print >> sys.stderr, "Loading source:",
    sourceElements = CorpusElements.loadCorpus(source, parse, tokenization)
    sourceSentencesByText = {}
    for sentence in sourceElements.sentences:
        sentenceText = sentence.sentence.get("text")
        #assert not sourceSentencesByText.has_key(sentenceText)
        if sourceSentencesByText.has_key(sentenceText):
            print >> sys.stderr, "Duplicate text", sentence.sentence.get("id"), sourceSentencesByText[sentenceText].sentence.get("id") 
        sourceSentencesByText[sentenceText] = sentence
    parsesCopied = [0,0]
    tokenizationsCopied = [0,0]
    for sentence in inputRoot.getiterator("sentence"):
        parsesCopied[1] += 1
        tokenizationsCopied[1] += 1
        #sourceSentence = sourceElements.sentencesByOrigId[sentence.attrib["origId"]]
        if not sourceSentencesByText.has_key(sentence.get("text")):
            print >> sys.stderr, "Warning, no text found for sentence", sentence.get("id")
            continue
        sourceSentence = sourceSentencesByText[sentence.get("text")]
        # Create analyses element (if needed)
        targetAnalysesElement = sentence.find("sentenceanalyses")
        if targetAnalysesElement == None:
            targetAnalysesElement = ET.Element("sentenceanalyses")
            sentence.append(targetAnalysesElement)
        # Create parses element (if needed)
        targetParsesElement = targetAnalysesElement.find("parses")
        if targetParsesElement == None:
            targetParsesElement = ET.Element("parses")
            targetAnalysesElement.append(targetParsesElement)
        # Check whether parse already exists
        targetParseElements = targetParsesElement.findall("parse")
        newParse = None
        for parseElement in targetParseElements:
            if parseElement.get("parser") == parse:
                newParse = parseElement
                break
        # Copy parse if it doesn't
        if newParse == None and sourceSentence.parseElement != None:
            targetParsesElement.append(sourceSentence.parseElement)
            parsesCopied[0] += 1
        
        # Create tokenizations element (if needed)
        targetTokenizationsElement = targetAnalysesElement.find("tokenizations")
        if targetTokenizationsElement == None:
            targetTokenizationsElement = ET.Element("tokenizations")
            targetAnalysesElement.append(targetTokenizationsElement)
        # Check whether tokenization already exists
        targetTokenizationElements = targetTokenizationsElement.findall("tokenization")
        newTokenization = None
        for tokenizationElement in targetTokenizationElements:
            if tokenizationElement.attrib["tokenizer"] == newParse.attrib["tokenizer"]:
                newTokenization = tokenizationElement
                break
        # Copy parse if it doesn't
        if newTokenization == None and sourceSentence.tokenizationElement != None:
            targetTokenizationsElement.append(sourceSentence.tokenizationElement)
            tokenizationsCopied[0] += 1
    
    print >> sys.stderr, "Copied parse elements", parsesCopied
    print >> sys.stderr, "Copied tokenization elements", tokenizationsCopied
    
    if output != None:       
        print >> sys.stderr, "Writing output to", output
        ETUtils.write(inputTree, output)
    return inputTree
        
if __name__=="__main__":
    print >> sys.stderr, "##### Copy Parse #####"
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"

    optparser = OptionParser(usage="%prog [options]\nCreate an html visualization for a corpus.")
    optparser.add_option("-i", "--input", default=None, dest="input", help="Corpus in analysis format", metavar="FILE")
    optparser.add_option("-s", "--source", default=None, dest="source", help="Corpus in analysis format", metavar="FILE")
    optparser.add_option("-o", "--output", default=None, dest="output", help="Corpus in analysis format", metavar="FILE")
    optparser.add_option("-t", "--tokenization", default=None, dest="tokenization", help="Tokenization element name")
    optparser.add_option("-p", "--parse", default=None, dest="parse", help="Parse element name")
    (options, args) = optparser.parse_args()
    assert(options.input != None)
    assert(options.source != None)
    assert(options.output != None)
    copyParse(options.input, options.source, options.output, options.parse, options.tokenization)