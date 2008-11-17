try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET
import cElementTreeUtils as ETUtils

if __name__=="__main__":
    import sys
    print >> sys.stderr, "##### Group sentences to documents by Pubmed article ids #####"
    
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
    optparser = OptionParser(usage="%prog [options]\nPath generator.")
    optparser.add_option("-i", "--input", default=defaultCorpusFilename, dest="input", help="Corpus in interaction xml format", metavar="FILE")
    optparser.add_option("-o", "--output", default=defaultOutputName, dest="output", help="Output file in interaction xml format.")
#    optparser.add_option("-v", "--verbose", dest="verbose", default=False, help="Verbose output.", action="store_true")
    (options, args) = optparser.parse_args()
    
    if options.input == None:
        print >> sys.stderr, "Error, input file not defined."
        optparser.print_help()
        sys.exit(1)
    if options.output == None:
        print >> sys.stderr, "Error, output file not defined."
        optparser.print_help()
        sys.exit(1)

    print >> sys.stderr, "Loading corpus file", options.input
    corpusTree = ET.parse(options.input)
    print >> sys.stderr, "Corpus file loaded"
    corpusRoot = corpusTree.getroot()
        
    # Group sentences by document
    print >> sys.stderr, "Grouping sentences by document"
    documents = corpusRoot.findall("document")
    newDocumentCount = 0
    docByPubmedId = {}
    for document in documents:
        corpusRoot.remove(document)
        sentences = document.findall("sentence")
        for sentence in sentences:
            if not docByPubmedId.has_key(sentence.attrib["PMID"]):
                newDocument = ET.Element("document")
                newDocument.attrib["id"] = "BioInfer.d" + str(newDocumentCount)
                newDocumentCount += 1
                newDocument.attrib["PMID"] = sentence.attrib["PMID"]
                docByPubmedId[sentence.attrib["PMID"]] = newDocument
                corpusRoot.append(newDocument)
            else:
                newDocument = docByPubmedId[sentence.attrib["PMID"]]
            newDocument.append(sentence)
    
    print >> sys.stderr, "Writing output to", options.output
    ETUtils.write(corpusRoot, options.output)
