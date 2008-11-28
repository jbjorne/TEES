import sys, os
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET
import cElementTreeUtils as ETUtils

if __name__=="__main__":
    from optparse import OptionParser
    optparser = OptionParser(usage="%prog [options]\nCopy elements from one interaction XML file to another.")
    optparser.add_option("-i", "--input", default=None, dest="input", help="File from which is read the XML-structure from which elements are copied", metavar="FILE")
    optparser.add_option("-o", "--output", default=None, dest="output", help="The file to which the new XML structure is saved. If None, will be the same as target.", metavar="FILE")
    optparser.add_option("-p", "--parse1", default=None, dest="parse1", help="parse element name")
    optparser.add_option("-q", "--parse2", default=None, dest="parse2", help="parse element name")
    optparser.add_option("-n", "--name", default=None, dest="name", help="New parse element name")
    (options, args) = optparser.parse_args()

    print >> sys.stderr, "Loading input file", options.input
    sourceTree = ET.parse(options.input)
    sourceRoot = sourceTree.getroot()
    
    print >> sys.stderr, "Merging parses"
    parsesElements = sourceRoot.getiterator("parses")
    for parsesElement in parsesElements:
        newParse = ET.Element(options.name)
        for parseElement in parsesElement.findall("parse"):
            if parseElement.
                parse1 = parsesElement
        for dependencyElement in bioinferGSParse.findall("dependency"):
            newParse.append(dependencyElement)
        parse2 = parsesElement.find(options.parse2)
        for dependencyElement in bioinferUncollapsedParse.findall("dependency"):
            newParse.append(dependencyElement)
        parsesElement.append(newParse)
    
    print >> sys.stderr, "Writing output", options.output
    ETUtils.write(sourceRoot, options.output)


