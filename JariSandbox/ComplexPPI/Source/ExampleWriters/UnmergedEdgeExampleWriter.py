import sys
from SentenceExampleWriter import SentenceExampleWriter
import InteractionXML.IDUtils as IDUtils
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET

class UnmergedEdgeExampleWriter(SentenceExampleWriter):
    def __init__(self):
        self.xType = "ue"
    
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
        
        # remove negative predicted entities
        self.removeChildren(sentenceElement, ["entity"], {"type":"neg"})
        
        # add required entities for dummy nodes with positive interactions
        dummies = {}
        newEntityIdCount = IDUtils.getNextFreeId(sentenceElement.findall("entity"))
        for example in examples:
            prediction = predictionsByExample[example[0]]
            if self.isNegative(prediction, classSet):
                continue
            assert example[3]["d1"] in ["T","F"], ("Example d1 error:", example)
            assert example[3]["d2"] in ["T","F"], ("Example d2 error:", example)
            for node in ["1","2"]:
                d = example[3]["d"+node]
                if d == "T": # Node is a dummy node
                    e = example[3]["e"+node]
                    l = example[3]["l"+node]
                    if not dummies.has_key(e): dummies[e] = {}
                    if not dummies[e].has_key(l): # Create a real node for the empty slot
                        entityElement = ET.Element("entity")
                        entityElement.attrib["isName"] = "False"
                        headToken = example[3]["t"+node]
                        for token in sentenceObject.tokens:
                            if token.get("id") == headToken:
                                headToken = token
                                break
                        entityElement.set("charOffset", headToken.get("charOffset")) 
                        entityElement.set("headOffset", headToken.get("charOffset"))
                        entityElement.set("text", headToken.get("text"))
                        entityElement.set("id", sentenceId + ".e" + str(newEntityIdCount))
                        #self.setElementType(entityElement, prediction, classSet, classIds)
                        entityElement.set("type", sentenceObject.entitiesById[e].get("type"))
                        # Add element to sentence
                        newEntityIdCount += 1
                        sentenceElement.append(entityElement)
                        # Keep track of created dummies
                        dummies[e][l] = entityElement
        
        # add interactions
        pairCount = 0
        for example in examples:
            prediction = predictionsByExample[example[0]]
            if self.isNegative(prediction, classSet):
                continue
            pairElement = ET.Element("interaction")
            pairElement.attrib["directed"] = "Unknown"
            if example[3]["d1"] == "F":
                pairElement.attrib["e1"] = example[3]["e1"]
            else:
                pairElement.attrib["e1"] = dummies[example[3]["e1"]][example[3]["l1"]].get("id")
            if example[3]["d2"] == "F":
                pairElement.attrib["e2"] = example[3]["e2"]
            else:
                pairElement.attrib["e2"] = dummies[example[3]["e2"]][example[3]["l2"]].get("id")
            pairElement.attrib["id"] = sentenceId + ".i" + str(pairCount)
            self.setElementType(pairElement, prediction, classSet, classIds)
            sentenceElement.append(pairElement)
            pairCount += 1
  
        # re-attach the analyses-element
        if sentenceAnalysesElement != None:
            sentenceElement.append(sentenceAnalysesElement)
