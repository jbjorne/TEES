import sys, os, copy
extraPath = os.path.dirname(os.path.abspath(__file__))+"/../../"
sys.path.append(extraPath)
from Utils.ProgressCounter import ProgressCounter
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET
import Utils.ElementTreeUtils as ETUtils
import IDUtils

# Splits merged types generated from overlapping entities/edges into their components
def getElementTypes(element, separator="---"):
    typeName = element.get("type")
    if typeName.find(separator) != -1:
        return typeName.split(separator)
    else:
        return [typeName]
    
def splitMerged(sentence, elementName, countsByType):
    elements = sentence.findall(elementName)
    elementCount = len(elements)
    newElements = []
    # split old elements and remove them
    removeCount = 0
    newIdCount = IDUtils.getNextFreeId(elements)
    for element in elements:
        types = getElementTypes(element)
        if len(types) > 1:
            for type in types:
                #newElement = copy.deepcopy(element)
                newElement = ET.Element(elementName)
                for k,v in element.attrib.iteritems():
                    newElement.set(k, v)
                newElement.set("type", type)
                idSplits = element.get("id").rsplit(".",1)
                newElement.set("id", idSplits[0] + "." + idSplits[1][0] + str(newIdCount) )
                newIdCount += 1
                #print "new id", idSplits[0] + "." + idSplits[1][0] + str(elementCount)
                newElements.append(newElement)
                elementCount += 1
            sentence.remove(element)
            removeCount += 1
    # insert the new elements
    elements = sentence.findall(elementName)
    if len(newElements) > 0:
        insertPos = 0
        if len(elements) > 0:
            for element in sentence:
                if element == elements[-1]:
                    break
                insertPos += 1
        for newElement in newElements:
            sentence.insert(insertPos, newElement)
    # increment counts
    if countsByType != None:
        countsByType[elementName][0] += removeCount
        countsByType[elementName][1] += len(newElements)
            
# Splits entities/edges with merged types into separate elements
def processSentence(sentence, countsByType):
    splitMerged(sentence, "entity", countsByType)
    splitMerged(sentence, "interaction", countsByType)
    splitMerged(sentence, "pair", countsByType)

def splitMergedElements(inputFilename, outputFilename=None):
    print >> sys.stderr, "##### Split elements with merged types #####"
    print >> sys.stderr, "Loading corpus", inputFilename
    corpusTree = ETUtils.ETFromObj(inputFilename)
    corpusRoot = corpusTree.getroot()
    
    documents = corpusRoot.findall("document")
    counter = ProgressCounter(len(documents), "Documents")
    countsByType = {"entity":[0,0], "interaction":[0,0], "pair":[0,0]}
    for document in documents:
        counter.update()
        for sentence in document.findall("sentence"):
            processSentence(sentence, countsByType)
    print >> sys.stderr, "Results"
    for k in sorted(countsByType.keys()):
        print >> sys.stderr, "  " + k + ": removed", countsByType[k][0], "created", countsByType[k][1]
    
    if outputFilename != None:
        print >> sys.stderr, "Writing output to", outputFilename
        ETUtils.write(corpusRoot, outputFilename)
    return corpusTree

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

    optparser = OptionParser(usage="%prog [options]\nPath generator.")
    optparser.add_option("-i", "--input", default=None, dest="input", help="Corpus in interaction xml format", metavar="FILE")
    optparser.add_option("-o", "--output", default=None, dest="output", help="Output file in interaction xml format.")
    (options, args) = optparser.parse_args()
    
    if options.input == None:
        print >> sys.stderr, "Error, input file not defined."
        optparser.print_help()
        sys.exit(1)
    if options.output == None:
        print >> sys.stderr, "Error, output file not defined."
        optparser.print_help()
        sys.exit(1)
    
    run(options.input, options.output)
