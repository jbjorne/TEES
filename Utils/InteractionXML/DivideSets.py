import sys, os
thisPath = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(thisPath,"../..")))
from Utils.ProgressCounter import ProgressCounter
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET
import Utils.ElementTreeUtils as ETUtils

def processCorpus(input, outDir, stem=None, tail=".xml", mergedSets=[], saveCombined=False, verbose=False):
    newCorpora = {}
    print >> sys.stderr, "Loading corpus file", input
    corpusRoot = ETUtils.ETFromObj(input).getroot()
    
    documents = corpusRoot.findall("document")
    counter = ProgressCounter(len(documents), "Documents")
    countsByType = {}
    for document in documents:
        counter.update()
        docSet = document.get("set")
        if docSet == None:
            if verbose: print >> sys.stderr, "Warning, no set defined for document", document.get("id")
            if not countsByType.has_key("No set"):
                countsByType["No set"] = 0
            countsByType["No set"] += 1
            continue
        elif not newCorpora.has_key(docSet):
            newCorpora[docSet] = ET.Element("corpus")
            for k, v in corpusRoot.attrib.iteritems():
                newCorpora[docSet].set(k, v)
            countsByType[docSet] = 0
        newCorpora[docSet].append(document)
        countsByType[docSet] += 1
        
    # Make merged sets
    for mergedSet in mergedSets:
        tag = "-and-".join(sorted(mergedSet))
        if not newCorpora.has_key(tag):
            newCorpora[tag] = ET.Element("corpus")
            for k, v in corpusRoot.attrib.iteritems():
                newCorpora[tag].set(k, v)
            countsByType[tag] = 0    
        for componentSet in mergedSet:
            for element in newCorpora[componentSet].findall("document"):
                newCorpora[tag].append(element)
                countsByType[tag] += 1
        
    print >> sys.stderr, "Documents per set"
    for k in sorted(countsByType.keys()):
        print >> sys.stderr, "  " + str(k) + ":", countsByType[k]
    
    if stem == None:
        outDir, stem = os.path.dirname(outDir), os.path.basename(outDir)
    if not os.path.exists(outDir):
        os.makedirs(outDir)
    
    print >> sys.stderr, "Writing output files to directory", outDir
    if saveCombined:
        print >> sys.stderr, "Saving combined input to", stem + tail
        ETUtils.write(corpusRoot, stem + tail)
    else:
        print >> sys.stderr, "Combined input not saved"
    for docSet in sorted(newCorpora.keys()):
        outFilename = os.path.join(outDir, stem + "-" + docSet + tail)
        print >> sys.stderr, "Writing set", docSet, "to", outFilename
        ETUtils.write(newCorpora[docSet], outFilename)

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
    optparser.add_option("-s", "--stem", default=None, dest="stem", help="Output file stem.")
    optparser.add_option("-t", "--tail", default=None, dest="tail", help="Output file tail.")
    optparser.add_option("-m", "--merged", default=None, dest="merged", help="Output file tail.")
    (options, args) = optparser.parse_args()
    
    if options.input == None:
        print >> sys.stderr, "Error, input file not defined."
        optparser.print_help()
        sys.exit(1)
    if options.output == None:
        print >> sys.stderr, "Error, output directory not defined."
        optparser.print_help()
        sys.exit(1)
    if options.stem == None:
        print >> sys.stderr, "Error, output stem not defined."
        optparser.print_help()
        sys.exit(1)
    if options.tail == None:
        print >> sys.stderr, "Error, output tail not defined."
        optparser.print_help()
        sys.exit(1)

    processCorpus(options.input, options.output, options.stem, options.tail)
