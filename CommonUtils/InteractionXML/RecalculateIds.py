try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET
import cElementTreeUtils as ETUtils

if __name__=="__main__":
    import sys
    print >> sys.stderr, "##### Recalculate hierarchical interaction XML ids #####"
    
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

    # Rebuild hierarchical ids
    print >> sys.stderr, "Recalculating interaction xml ids"
    corpusName = corpusRoot.attrib["source"]
    documents = corpusRoot.findall("document")
    docIndex = 0
    for document in documents:
        document.attrib["id"] = corpusName + ".d" + str(docIndex)
        sentences = document.findall("sentence")
        sentIndex = 0
        for sentence in sentences:
            sentence.attrib["id"] = corpusName + ".d" + str(docIndex) + ".s" + str(sentIndex)
            entities = sentence.findall("entity")
            entIndex = 0
            entDictionary = {}
            for entity in entities:
                entNewId = corpusName + ".d" + str(docIndex) + ".s" + str(sentIndex) + ".e" + str(entIndex)
                entDictionary[entity.attrib["id"]] = entNewId
                entity.attrib["id"] = entNewId
                entIndex += 1
            interactions = sentence.findall("interaction")
            intIndex = 0
            for interaction in interactions:
                interaction.attrib["id"] = corpusName + ".d" + str(docIndex) + ".s" + str(sentIndex) + ".i" + str(intIndex)
                interaction.attrib["e1"] = entDictionary[interaction.attrib["e1"]]
                interaction.attrib["e2"] = entDictionary[interaction.attrib["e2"]]
                intIndex += 1
            pairs = sentence.findall("pair")
            pairIndex = 0
            for pair in pairs:
                pair.attrib["id"] = corpusName + ".d" + str(docIndex) + ".s" + str(sentIndex) + ".p" + str(pairIndex)
                if entDictionary.has_key(pair.attrib["e1"]):
                    pair.attrib["e1"] = entDictionary[pair.attrib["e1"]]
                else:
                    pair.attrib["e1"] = "UNKNOWN"
                if entDictionary.has_key(pair.attrib["e2"]):
                    pair.attrib["e2"] = entDictionary[pair.attrib["e2"]]
                else:
                    pair.attrib["e2"] = "UNKNOWN"
                pairIndex += 1
            sentIndex += 1
        docIndex += 1
    
    print >> sys.stderr, "Writing output to", options.output
    ETUtils.write(corpusRoot, options.output)
