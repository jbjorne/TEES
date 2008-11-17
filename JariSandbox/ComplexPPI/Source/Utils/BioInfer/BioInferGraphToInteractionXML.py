import BIGraph.core.corpus
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET
import cElementTreeUtils as ETUtils
from optparse import OptionParser
import sys
import Range

def getTextByOffsets(offsets, sentenceText):
    texts = []
    for offset in offsets:
        texts.append(sentenceText[offset[0]:offset[1]+1])
    return texts

def getEntityOffset(subTokens, sentenceText):
    offsetBegins = []
    offsetEnds = []
    for subToken in subTokens:
        offsetBegins.append(int(subToken.offset_bgn))
        offsetEnds.append(int(subToken.offset_end))  
    offsetBegins.sort()
    offsetEnds.sort()
    
    for i in range(1, len(offsetBegins)):
        if offsetEnds[i-1] < offsetBegins[i]:
            if offsetEnds[i-1] + 1 == offsetBegins[i] or sentenceText[ offsetEnds[i-1] + 1 : offsetBegins[i] ].isspace():
                offsetEnds[i-1] = offsetBegins[i]
    
    entityOffset = []
    beginPos = offsetBegins[0]
    for i in range(len(offsetBegins)-1):
        if offsetEnds[i] != offsetBegins[i+1]:
            entityOffset.append( (beginPos, offsetEnds[i]) )
            beginPos = offsetBegins[i+1]
    entityOffset.append( (beginPos, offsetEnds[-1]))
    return entityOffset

def buildDocumentElement(id):
    documentElement = ET.Element("document")
    documentElement.attrib["id"] = id
    return documentElement

def buildSentenceElement(id, text, origId, PMID):
    sentenceElement = ET.Element("sentence")
    sentenceElement.attrib["id"] = id
    sentenceElement.attrib["origId"] = origId
    sentenceElement.attrib["PMID"] = PMID
    sentenceElement.attrib["text"] = text
    return sentenceElement

def buildEntityElement(interactionGraphNode, sentenceText):
    entityElement = ET.Element("entity")
    subTokens = interactionGraphNode.entity.token.getNested()
    startPos = int(subTokens[0].offset_bgn)
    offset = getEntityOffset(subTokens, sentenceText)
    entityElement.attrib["charOffset"] = Range.tuplesToCharOffset(offset)
    entityElement.attrib["origId"] = interactionGraphNode.entity.id
    entityElement.attrib["id"] = None
    entityElement.attrib["type"] = interactionGraphNode.entity.type
    texts = getTextByOffsets(offset, sentenceText)
    if len(texts) == 1:
        entityElement.attrib["text"] = texts[0]
    else:
        entityElement.attrib["text"] = str(texts)
    return (entityElement, startPos)

def buildInteractionElement(interactionGraphEdge, entityIdByOrigId):
    interactionElement = ET.Element("interaction")
    interactionElement.attrib["origId"] = edge[2].id
    interactionElement.attrib["type"] = edge[2].type
    interactionElement.attrib["e1"] = entityIdByOrigId[edge[2].bgn.entity.id]
    interactionElement.attrib["e2"] = entityIdByOrigId[edge[2].end.entity.id]
    interactionElement.attrib["directed"] = "True"
    return interactionElement
            
def compareStartPos(x, y):
    if x[1]>y[1]:
       return 1
    elif x[1]==y[1]:
       return 0
    else: # x<y
       return -1

def compareInteractionOrigId(x, y):
    x = int(x.attrib["origId"].rsplit(".",1)[-1])
    y = int(y.attrib["origId"].rsplit(".",1)[-1])
    if x>y:
       return 1
    elif x==y:
       return 0
    else: # x<y
       return -1

if __name__=="__main__":
    print >> sys.stderr, "##### Convert graph-format BioInfer to interaction XML #####"
    
    defaultGraphBioInferFilename = "/usr/share/biotext/BinaryBioInfer/BI.all.nestingresolved.identityresolved.anonymousResolved.relaxed.visibleSet.xml"
    defaultAnalysisFilename = "/usr/share/biotext/Tampere_project/PPI_Learning/Data/BioInfer/BioInferAnalysisWithGSAllSplitsVisible.xml"
#    defaultAnalysisFilename = "/usr/share/biotext/Tampere_project/PPI_Learning/Data/BioInfer/BioInferAnalysisWithGSWithParallelVisible.xml"
#    defaultAnalysisFilename = "/usr/share/biotext/Tampere_project/PPI_Learning/Data/BioInfer/BioInferAnalysisWithGSVisible_withsplit.xml"
#    defaultAnalysisFilename = "/usr/share/biotext/Tampere_project/PPI_Learning/Data/BioInfer/BioInferAnalysisWithGSVisible.xml"
#    defaultAnalysisFilename = "Data/BioInferVisible.xml"
    optparser = OptionParser(usage="%prog [options]\nCreate an html visualization for a corpus.")
    optparser.add_option("-i", "--input", default=defaultGraphBioInferFilename, dest="input", help="Graph BioInfer file", metavar="FILE")
    optparser.add_option("-o", "--output", default=None, dest="output", help="Output interaction xml file.")
#    optparser.add_option("-m", "--merge", dest="mergeBinaryRelations", default=False, help="", action="store_true")
    (options, args) = optparser.parse_args()
    
    assert(options.output != None)
     
    corpusBI = BIGraph.core.corpus.Corpus()
    print >> sys.stderr, "Reading corpus from", options.input
    corpusBI.readFromFile(options.input)
    
    corpusRoot = ET.Element("corpus")
    corpusRoot.attrib["source"] = "BioInfer"
    sentenceCount = 0
    for sentence in corpusBI.sentences:
        documentId = "BioInfer.d" + str(sentenceCount)
        sentenceId = documentId + ".s" + str(sentenceCount)
        #import inspect
        #print inspect.getmembers(sentence)
        
        documentElement = buildDocumentElement(documentId)
        corpusRoot.append(documentElement)
        sentenceElement = buildSentenceElement(sentenceId, sentence.text, sentence.id, sentence.PMID)
        documentElement.append(sentenceElement)
        
        interactionGraph = sentence.interactions
        edges = interactionGraph.edges()
        nodes = interactionGraph.nodes()
        
        nodeElements = []
        for node in nodes:
            nodeElements.append(buildEntityElement(node, sentence.text))
        nodeElements.sort(compareStartPos)
        # Add hierarchical ids
        entityCount = 0
        for pair in nodeElements:
            pair[0].attrib["id"] = sentenceId + ".e" + str(entityCount)
            sentenceElement.append(pair[0])
            entityCount += 1
        # Make a dictionary for resolving interaction ids
        entityIdByOrigId = {}
        for pair in nodeElements:
            entityIdByOrigId[pair[0].get("origId")] = pair[0].get("id")
        
        interactionElements = []
        for edge in edges:
            interactionElements.append(buildInteractionElement(edge, entityIdByOrigId))
        interactionElements.sort(compareInteractionOrigId)
        # Add hierarchical ids
        interactionCount = 0
        for interactionElement in interactionElements:
            interactionElement.attrib["id"] = sentenceId + ".i" + str(interactionCount)
            sentenceElement.append(interactionElement)
            interactionCount += 1
        
        sentenceCount += 1
    
    print >> sys.stderr, "Writing corpus to", options.output
    ETUtils.write(corpusRoot, options.output)
        
