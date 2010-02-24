import sys
from SentenceExampleWriter import SentenceExampleWriter
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET

class EdgeExampleWriter(SentenceExampleWriter):
    def __init__(self):
        self.xType = "edge"
    
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
    
        pairCount = 0
        for example in examples:
            prediction = predictionsByExample[example[0]]
            pairElement = ET.Element("interaction")
            pairElement.attrib["directed"] = "Unknown"
            pairElement.attrib["e1"] = example[3]["e1"] #.attrib["id"]
            pairElement.attrib["e2"] = example[3]["e2"] #.attrib["id"]
            pairElement.attrib["id"] = sentenceId + ".i" + str(pairCount)
            self.setElementType(pairElement, prediction, classSet, classIds)
            sentenceElement.append(pairElement)
            pairCount += 1
  
        # re-attach the analyses-element
        if sentenceAnalysesElement != None:
            sentenceElement.append(sentenceAnalysesElement)
