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
            #if self.isNegative(prediction, classSet):
            #    continue
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
                        newEntityId = entityElement.get("id")
                        #print "newEntityId",newEntityId
                        assert not sentenceObject.entitiesById.has_key(newEntityId)
                        sentenceObject.entitiesById[newEntityId] = entityElement
                        # Keep track of created dummies
                        dummies[e][l] = entityElement

        # select examples for correct edge combinations
        #print "DUMMIES", dummies
        #print sentenceObject.entitiesById
        examples = self.getValidExamples(examples, predictionsByExample, sentenceObject, dummies, classSet, classIds)
        
        # add interactions
        pairCount = 0
        for example in examples:
            prediction = predictionsByExample[example[0]]
            #if self.isNegative(prediction, classSet):
            #    continue
            pairElement = ET.Element("interaction")
            if example[3].has_key("discarded") and example[3]["discarded"]:
                pairElement.attrib["discarded"] = "True"
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
    
    def comparePredictions(self, p1, p2, classIndex, negIndex):
        if abs(p1[classIndex]-p1[negIndex]) > abs(p2[classIndex]-p2[negIndex]):
            return True
        else:
            return False
    
    def getValidExamples(self, examples, predictionsByExample, sentenceObject, dummies, classSet, classIds):
        predictionIndexByClassId = {}
        count = 1
        for classId in classIds:
            predictionIndexByClassId[classId] = count
            count += 1
        negClassId = classSet.getId("neg", False)
        negPredictionIndex = predictionIndexByClassId[negClassId]
        
        examplesByEntityByType = {}
        for example in examples:
            prediction = predictionsByExample[example[0]]
            if self.isNegative(prediction, classSet):
                continue
            
            if example[3]["d1"] == "F":
                e1 = example[3]["e1"]
            else:
                e1 = dummies[ example[3]["e1"] ][ example[3]["l1"] ].get("id")
                
            if not examplesByEntityByType.has_key(e1): 
                examplesByEntityByType[e1] = {}
            eType = classSet.getName(predictionsByExample[example[0]][0])
            if not examplesByEntityByType[e1].has_key(eType): 
                examplesByEntityByType[e1][eType] = []
            examplesByEntityByType[e1][eType].append(example)
        
        examplesToKeep = []
        for entityId, entityExamples in examplesByEntityByType.iteritems():
            entity = sentenceObject.entitiesById[entityId]
            entityType = entity.get("type")
            # Remove extra themes
            if entityExamples.has_key("Theme"):
                themeClassId = classSet.getId("Theme", False)
                themePredictionIndex = predictionIndexByClassId[themeClassId]
                themeExamples = entityExamples["Theme"]
                if len(themeExamples) <= 1:
                    examplesToKeep.extend(themeExamples)
                elif entityType != "Binding":
                    best = themeExamples[0]
                    for themeExample in themeExamples:
                        if self.comparePredictions(predictionsByExample[themeExample[0]], predictionsByExample[best[0]], themePredictionIndex, negPredictionIndex):
                        #if predictionsByExample[themeExample[0]][themePredictionIndex] > predictionsByExample[best[0]][themePredictionIndex]:
                            best = themeExample
                    examplesToKeep.append(best)
                else:
                    examplesToKeep.extend(themeExamples)
            themeExamples = None
            themeExample = None
            themePredictionIndex = None
            # Remove invalid causes
            if entityExamples.has_key("Cause"):
                if entityType.find("egulation") != -1:
                    causeExamples = entityExamples["Cause"]
                    if len(causeExamples) <= 1:
                        examplesToKeep.extend(causeExamples)
                    else:
                        causeClassId = classSet.getId("Cause", False)
                        causePredictionIndex = predictionIndexByClassId[causeClassId]
                        best = causeExamples[0]
                        for causeExample in causeExamples:
                            if self.comparePredictions(predictionsByExample[causeExample[0]], predictionsByExample[best[0]], causePredictionIndex, negPredictionIndex):
                            #if predictionsByExample[causeExample[0]][causePredictionIndex] > predictionsByExample[best[0]][causePredictionIndex]:
                                best = causeExample
                        examplesToKeep.append(best)
        for example in examples:
            example[3]["discarded"] = False
            if example not in examplesToKeep:
                if predictionsByExample[example[0]][0] != 1:
                    example[3]["discarded"] = True
                    predictionsByExample[example[0]][0] = 1
        return examples
                    