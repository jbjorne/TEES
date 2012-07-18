__version__ = "$Revision: 1.2 $"

import sys,os
import sys
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET
import Utils.ElementTreeUtils as ETUtils

def convert(input, output=None, outputRoot=None):
    print >> sys.stderr, "##### Convert PMC to Interaction XML #####"
    
    print >> sys.stderr, "Loading corpus", input
    pmcTree = ETUtils.ETFromObj(input)
    print >> sys.stderr, "Corpus file loaded"
    pmcRoot = pmcTree.getroot()
        
    includeElements = [
        "front",
        "article-meta",
        "title-group",
        "article-title",
        "abstract",
        "body",
        "sec",
        "p",
        "title"]
    collapseElements = [
        "front",
        "article-meta",
        "title-group",
        "p"]
    
    if outputRoot == None:
        outputRoot = ET.Element("corpus")
        outputRoot.set("source", "PMC")
    
    outputRoot.append(addElements(pmcRoot, includeElements, collapseElements))
    
    outputTree = ET.ElementTree(outputRoot)
    if output != None:
        print >> sys.stderr, "Writing output to", output
        ETUtils.write(outputTree, output)
    return outputTree
    
def addElements(pmcElement, includeElements, collapseElements, outputParent=None, pmcPath="", secCount = [0], articleId=None):
    stop = False
    if pmcElement.tag == "article":
        assert articleId == None
        outputParent = ET.Element("document")
        pmid = None
        for idElement in pmcElement.getiterator("article-id"):
            if idElement.get("pub-id-type") == "pmid":
                pmid = idElement.text
                break
        articleId = "PMC" + ".d" + str(pmid)
        outputParent.set("id", articleId)
    elif pmcElement.tag in includeElements:
        pmcElementText = getText(pmcElement)
        if (pmcElementText != None and pmcElementText.strip() != "") or pmcElement.tag not in collapseElements:
            section = ET.Element("section")
            section.set("id", articleId + ".c" + str(secCount[0]))
            secCount[0] += 1
            section.set("type", pmcElement.tag)
            pmcElementId = pmcElement.get("id")
            if pmcElementId != None:
                section.set("secId", pmcElementId)
            section.set("pmcPath", pmcPath)
            if pmcElementText != None:
                section.set("text", pmcElementText)
            outputParent.append(section)
            outputParent = section
    else:
        stop = True
    
    if not stop:
        childCounts = {}
        for pmcChild in list(pmcElement):
            childTag = pmcChild.tag
            if not childCounts.has_key(childTag):
                childCounts[childTag] = 0
            else:
                childCounts[childTag] += 1
            addElements(pmcChild, includeElements, collapseElements, outputParent, pmcPath + "/" + childTag + "-" + str(childCounts[childTag]), secCount, articleId)
    
    return outputParent

def getText(element):
    text = element.text
    if text == None or text == "":
        return text
    for child in list(element):
        assert child.tag in ("xref", "italic", "bold", "fig", "ext-link"), child.tag
        if child.text != None:
            text += child.text
        if child.tail != None:
            text += child.tail
    while text[-1] == "\n":
        text = text[:-1]
    return text

if __name__=="__main__":
    import sys
    
    from optparse import OptionParser
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"

    optparser = OptionParser(usage="%prog [options]\n")
    optparser.add_option("-i", "--input", default=None, dest="input", help="Corpus in interaction xml format", metavar="FILE")
    optparser.add_option("-o", "--output", default=None, dest="output", help="Output file in interaction xml format.")
    (options, args) = optparser.parse_args()
    
    convert(input=options.input, output=options.output)