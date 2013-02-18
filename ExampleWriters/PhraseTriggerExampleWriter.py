import sys
from SentenceExampleWriter import SentenceExampleWriter
import Utils.InteractionXML.IDUtils as IDUtils
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET
import Utils.Range as Range

class PhraseTriggerExampleWriter(SentenceExampleWriter):
    def __init__(self):
        self.xType = "phrase"
        SentenceExampleWriter.__init__(self)
    
    def writeXMLSentence(self, examples, predictionsByExample, sentenceObject, classSet, classIds, goldSentence=None, exampleStyle=None, structureAnalyzer=None):        
        self.assertSameSentence(examples)
        
        sentenceElement = sentenceObject.sentence
        sentenceId = sentenceElement.get("id")
        sentenceText = sentenceElement.get("text")
        # detach analyses-element
        sentenceAnalysesElement = None
        sentenceAnalysesElement = sentenceElement.find("sentenceanalyses")
        if sentenceAnalysesElement == None:
            sentenceAnalysesElement = sentenceElement.find("analyses")
        if sentenceAnalysesElement != None:
            sentenceElement.remove(sentenceAnalysesElement)
        # remove pairs and interactions
        interactions = self.removeChildren(sentenceElement, ["pair", "interaction"])
        # remove entities
        newEntityIdCount = IDUtils.getNextFreeId(sentenceElement.findall("entity"))
        nonNameEntities = self.removeNonNameEntities(sentenceElement)
            
        # add new pairs
        for example in examples:
            prediction = predictionsByExample[example[0]]
            entityElement = ET.Element("entity")
            #entityElement.attrib["given"] = "False"
            headToken = example[3]["t"]
            for token in sentenceObject.tokens:
                if token.get("id") == headToken:
                    headToken = token
                    break
            entityElement.set("charOffset", example[3]["charOffset"]) 
            entityElement.set("headOffset", headToken.get("charOffset"))
            entityElement.set("phraseType", example[3]["ptype"])
            entOffset = Range.charOffsetToSingleTuple(example[3]["charOffset"])
            entityElement.set("text", sentenceText[entOffset[0]:entOffset[1]])
            entityElement.set("id", sentenceId + ".e" + str(newEntityIdCount))
            self.setElementType(entityElement, prediction, classSet, classIds)
            newEntityIdCount += 1
            sentenceElement.append(entityElement)

        # re-attach the analyses-element
        if sentenceAnalysesElement != None:
            sentenceElement.append(sentenceAnalysesElement)