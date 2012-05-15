import sys
from SentenceExampleWriter import SentenceExampleWriter
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET

class EdgeExampleWriter(SentenceExampleWriter):
    def __init__(self):
        self.xType = "edge"
        self.removeEdges = True
        SentenceExampleWriter.__init__(self)
    
    def writeXMLSentence(self, examples, predictionsByExample, sentenceObject, classSet, classIds, goldSentence=None):        
        self.assertSameSentence(examples)
        
        sentenceElement = sentenceObject.sentence
        sentenceId = sentenceElement.get("id")
        # detach analyses-element
        sentenceAnalysesElement = None
        sentenceAnalysesElement = sentenceElement.find("sentenceanalyses")
        if sentenceAnalysesElement == None:
            sentenceAnalysesElement = sentenceElement.find("analyses")
        if sentenceAnalysesElement != None:
            sentenceElement.remove(sentenceAnalysesElement)
        # remove pairs and interactions
        if self.removeEdges:
            removed = self.removeChildren(sentenceElement, ["pair", "interaction"])
        
        causeAfterTheme = False
        pairCount = 0
        for example in examples:
            if example[3].has_key("causeAfterTheme"):
                causeAfterTheme = True
            prediction = predictionsByExample[example[0]]
            predictionString = self.getPredictionStrengthString(prediction, classSet, classIds)
            for iType in self.getElementTypes(prediction, classSet, classIds): # split merged classes
                pairElement = ET.Element("interaction")
                pairElement.set("directed", "Unknown")
                pairElement.set("e1", example[3]["e1"]) #.attrib["id"]
                if "e1DuplicateIds" in example[3]:
                    pairElement.set("e1DuplicateIds", example[3]["e1DuplicateIds"])
                pairElement.set("e2", example[3]["e2"]) #.attrib["id"]
                if "e2DuplicateIds" in example[3]:
                    pairElement.set("e2DuplicateIds", example[3]["e2DuplicateIds"])
                pairElement.set("id", sentenceId + ".i" + str(pairCount))
                pairElement.set("type", iType)
                pairElement.set("predictions", predictionString)
                #self.setElementType(pairElement, prediction, classSet, classIds)
                if pairElement.get("type") != "neg":
                    sentenceElement.append(pairElement)
                    pairCount += 1
        
        # Re-attach original themes, if needed
        if causeAfterTheme:
            for interaction in removed:
                if interaction.get("type") == "Theme":
                    interaction.set("id", sentenceId + ".i" + str(pairCount))
                    sentenceElement.append(interaction)
                    pairCount += 1
  
        # re-attach the analyses-element
        if sentenceAnalysesElement != None:
            sentenceElement.append(sentenceAnalysesElement)
