import sys, os
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET
import Utils.ElementTreeUtils as ETUtils

if __name__=="__main__":
    print >> sys.stderr, "##### Merge named entity types #####"
    from optparse import OptionParser
    optparser = OptionParser(usage="%prog [options]\n")
    optparser.add_option("-i", "--input", default=None, dest="input", help="", metavar="FILE")
    optparser.add_option("-o", "--output", default=None, dest="output", help="", metavar="FILE")
    (options, args) = optparser.parse_args()

    print >> sys.stderr, "Loading input file", options.input
    sourceTree = ET.parse(options.input)
    sourceRoot = sourceTree.getroot()
    
    print >> sys.stderr, "Merging named entity types"
    entities = sourceRoot.getiterator("entity")
    mergedByType = {}
    for entity in entities:
        if entity.attrib.has_key("given") and entity.attrib["given"] == "True":
            if not mergedByType.has_key(entity.attrib["type"]):
                mergedByType[entity.attrib["type"]] = 0
            mergedByType[entity.attrib["type"]] += 1
            entity.attrib["type"] = "Gene/protein/RNA"
    
    print >> sys.stderr, "Merged:"
    for k in sorted(mergedByType.keys()):
        print >> sys.stderr, "  " + k + ": " + str(mergedByType[k])
            
    print >> sys.stderr, "Writing output", options.output
    ETUtils.write(sourceRoot, options.output)


