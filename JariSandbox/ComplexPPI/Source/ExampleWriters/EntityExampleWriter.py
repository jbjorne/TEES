import sys
from SentenceExampleWriter import SentenceExampleWriter
import InteractionXML.IDUtils as IDUtils
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET

class EntityExampleWriter(SentenceExampleWriter):
    def __init__(self):
        self.xType = "token"
    
    def writeXMLSentence(self, examples, predictionsByExample, sentenceObject, classSet, classIds):        
        self.assertSameSentence(examples)
        
        sentenceElement = sentenceObject.sentence
        sentenceId = sentenceElement.get("id")
        # detach analyses-element
        sentenceAnalysesElement = None
        sentenceAnalysesElement = sentenceElement.find("sentenceanalyses")
        if sentenceAnalysesElement != None:
            sentenceElement.remove(sentenceAnalysesElement)
        # remove pairs and interactions
        self.removeChildren(sentenceElement, ["pair", "interaction"])
        # remove entities
        self.removeNonNameEntities(sentenceElement)

        # add new pairs
        newEntityIdCount = IDUtils.getNextFreeId(sentenceElement.findall("entity"))
        for example in examples:
            prediction = predictionsByExample[example[0]]
            entityElement = ET.Element("entity")
            entityElement.attrib["isName"] = "False"
            headToken = example[3]["t"]
            for token in sentenceObject.tokens:
                if token.get("id") == headToken:
                    headToken = token
                    break
            entityElement.attrib["charOffset"] = headToken.get("charOffset") 
            entityElement.attrib["headOffset"] = headToken.get("charOffset")
            entityElement.attrib["text"] = headToken.get("text")
            entityElement.attrib["id"] = sentenceId + ".e" + str(newEntityIdCount)
            self.setElementType(entityElement, prediction, classSet, classIds)
            newEntityIdCount += 1
            sentenceElement.append(entityElement)

        # re-attach the analyses-element
        if sentenceAnalysesElement != None:
            sentenceElement.append(sentenceAnalysesElement)
