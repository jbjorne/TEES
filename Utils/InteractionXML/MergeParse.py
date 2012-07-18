__version__ = "$Revision: 1.2 $"

try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET
import Utils.ElementTreeUtils as ETUtils
import sys
import CorpusElements
from optparse import OptionParser

if __name__=="__main__":
    print >> sys.stderr, "##### Merge Parse #####"
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"

    optparser = OptionParser(usage="%prog [options]\nCreate an html visualization for a corpus.")
    optparser.add_option("-i", "--input", default=None, dest="input", help="Corpus in analysis format", metavar="FILE")
    optparser.add_option("-o", "--output", default=None, dest="output", help="Corpus in analysis format", metavar="FILE")
    optparser.add_option("-p", "--parse1", default=None, dest="parse1", help="Parse element name")
    optparser.add_option("-q", "--parse2", default=None, dest="parse2", help="Parse element name")
    optparser.add_option("-n", "--name", default=None, dest="name", help="New parse element name")
    (options, args) = optparser.parse_args()
    assert(options.input != None)
    assert(options.output != None)
    
    print >> sys.stderr, "Loading input file", options.input
    inputRoot = ET.parse(options.input).getroot()
    for sentence in inputRoot.getiterator("sentence"):
        targetAnalysesElement = sentence.find("sentenceanalyses")
        assert(targetAnalysesElement != None)
        targetParsesElement = targetAnalysesElement.find("parses")
        assert(targetParsesElement != None)
        # Check whether parse already exists
        targetParseElements = targetParsesElement.findall("parse")
        parse1 = None
        parse2 = None
        for parseElement in targetParseElements:
            if parseElement.attrib["parser"] == options.parse1:
                parse1 = parseElement
            elif parseElement.attrib["parser"] == options.parse2:
                parse2 = parseElement
        assert(parse1 != parse2 and parse1 != None and parse2 != None)

        targetTokenizationsElement = targetAnalysesElement.find("tokenizations")
        assert(targetTokenizationsElement != None)
        tokenization1 = None
        tokenization2 = None
        for tokenizationElement in targetTokenizationsElement.findall("tokenization"):
            if tokenizationElement.attrib["tokenizer"] == parse1.attrib["tokenizer"]:
                tokenization1 = tokenizationElement
            if tokenizationElement.attrib["tokenizer"] == parse2.attrib["tokenizer"]:
                tokenization2 = tokenizationElement
        assert(tokenization1 == tokenization2 and tokenization1 != None and tokenization2 != None)
#        if tokenization1 != tokenization2:
#            tokens1 = tokenization1.findall("token")
#            tokens2 = tokenization1.findall("token")
#            assert(len(tokens1) == len(tokens2))
#            for i in range(len(tokens1)):
        newParse = ET.Element("parse")
        newParse.attrib["parser"] = options.name
        newParse.attrib["tokenizer"] = tokenization1.attrib["tokenizer"]
        for dependency in parse1.findall("dependency"):
            newParse.append(dependency)
        for dependency in parse2.findall("dependency"):
            newParse.append(dependency)
        targetParsesElement.append(newParse)
    print >> sys.stderr, "Writing output to", options.output
    ETUtils.write(inputRoot, options.output)