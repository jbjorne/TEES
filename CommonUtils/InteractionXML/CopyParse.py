try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET
import cElementTreeUtils as ETUtils
import sys
import CorpusElements
from optparse import OptionParser

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
    
    print >> sys.stderr, "Loading input file", options.input
    inputRoot = ET.parse(options.input).getroot()
    print >> sys.stderr, "Loading source:",
    sourceElements = CorpusElements.loadCorpus(options.source, options.parse, options.tokenization)
    parseCopied = None
    tokenizationCopied = None
    for sentence in inputRoot.getiterator("sentence"):
        sourceSentence = sourceElements.sentencesByOrigId[sentence.attrib["origId"]]
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
            if parseElement.attrib["parser"] == options.parse:
                newParse = parseElement
                #print >> sys.stderr, "Parse element", options.parse, "already exists, not copied."
                assert(parseCopied == None or parseCopied == False)
                parseCopied = False
                break
        # Copy parse if it doesn't
        if newParse == None:
            newParse = ET.Element("parse")
            newParse.attrib["parser"] = options.parse
            targetParsesElement.append(newParse)
            if sourceSentence.parseElement.attrib.has_key("tokenizer"):
                newParse.attrib["tokenizer"] = sourceSentence.parseElement.attrib["tokenizer"]
            else:
                newParse.attrib["tokenizer"] = options.tokenization
            for dependency in sourceSentence.dependencies:
                newParse.append(dependency)
            assert(parseCopied == None or parseCopied == True)
            parseCopied = True
            #print >> sys.stderr, "Copied parse element", options.parse
        
        # Create tokenization element (if needed)
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
                #print >> sys.stderr, "Tokenization element", newParse.attrib["tokenizer"], "already exists, not copied."
                assert(tokenizationCopied == None or tokenizationCopied == False)
                tokenizationCopied = False
                break
        # Copy parse if it doesn't
        if newTokenization == None:
            newTokenization = ET.Element("tokenization")
            newTokenization.attrib["tokenizer"] = newParse.attrib["tokenizer"]
            targetTokenizationsElement.append(newTokenization)
            for token in sourceSentence.tokens:
                newTokenization.append(token)
            assert(tokenizationCopied == None or tokenizationCopied == True)
            tokenizationCopied = True
            #print >> sys.stderr, "Copied tokenization element", newParse.attrib["tokenizer"]
    
    if parseCopied:
        print >> sys.stderr, "Copied parse elements", options.parse
    else:
        print >> sys.stderr, "Parse elements", options.parse, "already exist, not copied."
    if tokenizationCopied:
        print >> sys.stderr, "Copied tokenization elements", newParse.attrib["tokenizer"]
    else:
        print >> sys.stderr, "Tokenization elements", newParse.attrib["tokenizer"], "already exist, not copied."       
    print >> sys.stderr, "Writing output to", options.output
    ETUtils.write(inputRoot, options.output)