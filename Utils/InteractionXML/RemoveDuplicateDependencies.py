import sys, os
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET
import Utils.ElementTreeUtils as ETUtils

if __name__=="__main__":
    from optparse import OptionParser
    optparser = OptionParser(usage="%prog [options]\n")
    optparser.add_option("-i", "--input", default=None, dest="input", help="File from which is read the XML-structure from which elements are copied", metavar="FILE")
    optparser.add_option("-o", "--output", default=None, dest="output", help="The file to which the new XML structure is saved. If None, will be the same as target.", metavar="FILE")
    (options, args) = optparser.parse_args()

    print >> sys.stderr, "Loading input file", options.input
    sourceTree = ET.parse(options.input)
    sourceRoot = sourceTree.getroot()
    
    print >> sys.stderr, "Removing dependencies"
    parsesElements = sourceRoot.getiterator("parses")
    for parsesElement in parsesElements:
        for parseElement in parsesElement.findall("parse"):
            dependencies = parseElement.findall("dependency")
            toRemove = [False] * len(dependencies)
            for i in range(0, len(dependencies)-1):
                for j in range(i+1, len(dependencies)):
                    di = dependencies[i]
                    dj = dependencies[j]
                    if di.attrib["type"] == dj.attrib["type"] and di.attrib["t1"] == dj.attrib["t1"] and di.attrib["t2"] == dj.attrib["t2"]:
                        toRemove[j] = True
            count = 0
            for i in range(0, len(dependencies)):
                if toRemove[i]:
                    parseElement.remove(dependencies[i])
                    count += 1
            print >> sys.stderr, "Parse:", parseElement.attrib["parser"], "Removed:", count
    
    print >> sys.stderr, "Writing output", options.output
    ETUtils.write(sourceRoot, options.output)


