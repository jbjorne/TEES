import sys
from SentenceExampleWriter import SentenceExampleWriter
import InteractionXML.IDUtils as IDUtils
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET

class AsymmetricEventExampleWriter(SentenceExampleWriter):
    def __init__(self):
        self.xType = "asym"
    
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
        
        entityByTokenByType = {}
        # First add existing entities (names) (sentenceObject still has all entities)
        for entity in sentenceElement.findall("entity"):
            headOffset = entity.get("headOffset")
            headToken = None
            for token in sentenceObject.tokens:
                if token.get("charOffset") == headOffset:
                    headToken = token
                    break
            assert headToken != None
            headTokenId = headToken.get("id")
            if not entityByTokenByType.has_key(headTokenId):
                entityByTokenByType[headTokenId] = {}
            entityByTokenByType[headTokenId][entity.get("type")] = entity
        
        # Then add entities defined by examples
        newEntityIdCount = IDUtils.getNextFreeId(sentenceElement.findall("entity"))
        for example in examples:
            prediction = predictionsByExample[example[0]]
            if prediction[0] == 1:
                continue
            
            headTokenId = example[3]["t1"]
            if not entityByTokenByType.has_key(headTokenId):
                entityByTokenByType[headTokenId] = {}
            e1Type = classSet.getName(prediction[0])
            if e1Type == "Cause":
                continue
            
            # Maximum of one entity per type per token
            if entityByTokenByType[headTokenId].has_key(e1Type):
                continue
            
            entityElement = ET.Element("entity")
            entityByTokenByType[headTokenId][e1Type] = entityElement 
            entityElement.attrib["isName"] = "False"
            for token in sentenceObject.tokens:
                if token.get("id") == headTokenId:
                    headToken = token
                    break
            entityElement.attrib["charOffset"] = headToken.get("charOffset") 
            entityElement.attrib["headOffset"] = headToken.get("charOffset")
            entityElement.attrib["text"] = headToken.get("text")
            entityElement.attrib["id"] = sentenceId + ".e" + str(newEntityIdCount)
            entityElement.set("type", e1Type)
            newEntityIdCount += 1
            sentenceElement.append(entityElement)
    
        pairCount = 0
        for example in examples:
            prediction = predictionsByExample[example[0]]
            if prediction[0] == 1:
                continue
            exampleType = classSet.getName(prediction[0])
            t1Id = example[3]["t1"]
            t2Id = example[3]["t2"]
            
            if exampleType != "Cause":
                if entityByTokenByType.has_key(t2Id):
                    e1Id = entityByTokenByType[t1Id][exampleType].get("id")
                    for e2Type in sorted(entityByTokenByType[t2Id].keys()):
                        if exampleType.find("egulation") == -1 and e2Type != "Protein":
                            continue
                        pairElement = ET.Element("interaction")
                        pairElement.attrib["directed"] = "Unknown"
                        pairElement.attrib["e1"] = e1Id
                        pairElement.attrib["e2"] = entityByTokenByType[t2Id][e2Type].get("id")
                        pairElement.attrib["id"] = sentenceId + ".i" + str(pairCount)
                        pairElement.set("type", "Theme")
                        sentenceElement.append(pairElement)
                        pairCount += 1
            else:
                if entityByTokenByType.has_key(t1Id) and entityByTokenByType.has_key(t2Id): 
                    for e1Type in sorted(entityByTokenByType[t1Id].keys()):
                        if exampleType.find("egulation") == -1:
                            continue
                        for e2Type in sorted(entityByTokenByType[t2Id].keys()):
                            pairElement = ET.Element("interaction")
                            pairElement.attrib["directed"] = "Unknown"
                            pairElement.attrib["e1"] = entityByTokenByType[t1Id][e1Type].get("id")
                            pairElement.attrib["e2"] = entityByTokenByType[t2Id][e2Type].get("id")
                            pairElement.attrib["id"] = sentenceId + ".i" + str(pairCount)
                            pairElement.set("type", "Cause")
                            sentenceElement.append(pairElement)
                            pairCount += 1
  
        # re-attach the analyses-element
        if sentenceAnalysesElement != None:
            sentenceElement.append(sentenceAnalysesElement)
