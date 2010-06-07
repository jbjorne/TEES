import sys
from SentenceExampleWriter import SentenceExampleWriter
import InteractionXML.IDUtils as IDUtils
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET

class UnmergingExampleWriter(SentenceExampleWriter):
    def __init__(self):
        self.xType = "um"
    
    def writeXMLSentence(self, examples, predictionsByExample, sentenceObject, classSet, classIds):        
        sentenceElement = sentenceObject.sentence
        self.sentenceId = sentenceElement.get("id")
        self.assertSameSentence(examples, self.sentenceId)
        # detach analyses-element
        sentenceAnalysesElement = None
        sentenceAnalysesElement = sentenceElement.find("sentenceanalyses")
        if sentenceAnalysesElement != None:
            sentenceElement.remove(sentenceAnalysesElement)
                
        # remove pairs and interactions
        interactions = self.removeChildren(sentenceElement, ["pair", "interaction"])
        # remove entities
        entities = self.removeNonNameEntities(sentenceElement)
        
        interactionsByEntity = {}
        interactionsById = {}
        for entity in entities:
            interactionsByEntity[entity.get("id")] = []
        for interaction in interactions:
            e1Id = interaction.get("e1")
            if not interactionsByEntity.has_key(e1Id):
                interactionsByEntity[e1Id] = []
            interactionsByEntity[e1Id].append(interaction)
            interactionsById[interaction.get("id")] = interaction

        # NOTE! Following won't work for pairs
        self.entityCount = IDUtils.getNextFreeId(sentenceElement.findall("entity"))
        self.interactionCount = IDUtils.getNextFreeId(sentenceElement.findall("interaction"))
        self.newEntities = []
        self.newInteractions = []
        
        # Mapping for connecting the events
        self.entityByHeadByType = {}
        self.tokenByOffset = {}
        for token in sentenceObject.tokens:
            self.tokenByOffset[token.get("charOffset")] = token
            self.entityByHeadByType[token.get("charOffset")] = {}
        for entity in sentenceObject.entities:
            if entity.get("isName") != "True":
                continue
            offset = entity.get("headOffset")
            eType = entity.get("type")
            if not self.entityByHeadByType[offset].has_key(eType):
                self.entityByHeadByType[offset][eType] = []
            self.entityByHeadByType[offset][eType].append(entity)
        
        entityKeys = sentenceObject.entitiesById.keys()
        exampleByEntityId = {}
        for example in examples:
            eId = example[3]["e"]
            assert eId in entityKeys
            exampleByEntityId[eId] = example
        
        self.newEntitiesById = {}
        self.outEdgesByEntity = {}
        
        # Add the simple, one-argument events
        for entity in entities:
            # If no example, case is unambiguous
            if not exampleByEntityId.has_key(entity.get("id")):
                simpleEventInteractions = interactionsByEntity[entity.get("id")]
                numCauses = 0
                for interaction in simpleEventInteractions[:]:
                    if interaction.get("type") == "Cause":
                        numCauses += 1
                    if self.isIntersentence(interaction):
                        print "Warning, intersentence interaction for", entity.get("id"), entity.get("type")
                        simpleEventInteractions.remove(interaction)
                    if interaction.get("type") == "neg":
                        simpleEventInteractions.remove(interaction)
                if len(simpleEventInteractions) == 2 and numCauses == 1:
                    rootEntity = self.insertEvent(simpleEventInteractions, sentenceObject)
                    rootEntity.set("umType", "simple")
                else:
                    for interaction in simpleEventInteractions:
                        rootEntity = self.insertEvent([interaction], sentenceObject)
                        rootEntity.set("umType", "simple")
            
        # Add predicted, unmerged events
        for example in examples:
            #print predictionsByExample[example[0]]
            if predictionsByExample[example[0]][0] == 1: # negative
                continue
            arguments = []
            for iId in example[3]["i"].split(","):
                arg = interactionsById[iId]
                if self.isIntersentence(arg):
                    continue
                assert arg.get("type") != "neg"
                arguments.append(arg)
            rootEntity = self.insertEvent(arguments, sentenceObject)
            if rootEntity != None:
                rootEntity.set("umType", "complex")
        
        # Attach the new elements
        for element in self.newEntities + self.newInteractions:
            sentenceElement.append(element)

        # re-attach the analyses-element
        if sentenceAnalysesElement != None:
            sentenceElement.append(sentenceAnalysesElement)
    
    def insertEvent(self, arguments, sentenceObject):
        currentEntities = {} # Entities being part of the current event
        rootEntity = None
        for arg in arguments:
            e1Id = arg.get("e1")
            e2Id = arg.get("e2")
            # E1
            origE1 = sentenceObject.entitiesById[e1Id]
            e1HeadOffset = origE1.get("headOffset")
            e1Type = origE1.get("type")
            if e1Id not in currentEntities.keys():
                e1 = None
                if self.entityByHeadByType[e1HeadOffset].has_key(e1Type):
                    for entity in self.entityByHeadByType[e1HeadOffset][e1Type]:
                        if not self.outEdgesByEntity.has_key(entity):
                            e1 = entity
                            currentEntities[e1Id] = e1
                            break
                if e1 == None:
                    e1 = self.insertEntity(sentenceObject.entitiesById[e1Id])
                    currentEntities[e1Id] = e1
            else:
                e1 = currentEntities[e1Id]
            
            if rootEntity == None:
                rootEntity = e1
            else:
                assert rootEntity == e1
            # E2
            assert e2Id in sentenceObject.entitiesById.keys(), self.sentenceId + "/" + e2Id
            origE2 = sentenceObject.entitiesById[e2Id]
            e2HeadOffset = origE2.get("headOffset")
            e2Type = origE2.get("type")
            if e2Id not in currentEntities.keys():
                if self.entityByHeadByType[e2HeadOffset].has_key(e2Type):
                    e2 = self.entityByHeadByType[e2HeadOffset][e2Type][0]
                else:
                    e2 = self.insertEntity(sentenceObject.entitiesById[e2Id])
                    currentEntities[e2Id] = e2
            else:
                e2 = currentEntities[e2Id]
            self.insertInteraction(e1, e2, arg)
        return rootEntity
    
    def insertEntity(self, entity):
        entityElement = ET.Element("entity")
        assert entity.get("isName") != "True"
        entityElement.set("isName", "False")
        entityElement.set("charOffset", entity.get("charOffset"))
        entityElement.set("headOffset", entity.get("headOffset")) 
        entityElement.set("text", entity.get("text")) 
        entityElement.set("id", self.sentenceId + ".e" + str(self.entityCount))
        entityElement.set("type", entity.get("type"))
        if entity.get("predictions") != None:
            entityElement.set("predictions", entity.get("predictions"))
        self.newEntities.append(entityElement)
        self.entityCount += 1
        # new entity element by orig id
        #self.newEntityMap[entity.get("id")] = entityElement
        eType = entityElement.get("type")
        headOffset = entityElement.get("headOffset")
        if not self.entityByHeadByType[headOffset].has_key(eType):
            self.entityByHeadByType[headOffset][eType] = []
        self.entityByHeadByType[headOffset][eType].append(entityElement)
        return entityElement
    
    def insertInteraction(self, e1, e2, arg):
        interactionElement = ET.Element("interaction")
        interactionElement.attrib["directed"] = "Unknown"
        interactionElement.attrib["e1"] = e1.get("id")
        interactionElement.attrib["e2"] = e2.get("id")
        interactionElement.attrib["id"] = self.sentenceId + ".i" + str(self.interactionCount)
        interactionElement.set("type", arg.get("type"))
        if arg.get("predictions") != None:
            interactionElement.set("predictions", arg.get("predictions"))
        self.newInteractions.append(interactionElement)
        self.interactionCount += 1
        
        if not self.outEdgesByEntity.has_key(e1):
            self.outEdgesByEntity[e1] = []
        self.outEdgesByEntity[e1].append(interactionElement)
        
        return interactionElement
    
    def isIntersentence(self, interaction):
        e1MajorId, e1MinorId = interaction.get("e1").rsplit(".e", 1)
        e2MajorId, e2MinorId = interaction.get("e2").rsplit(".e", 1)
        return e1MajorId != e2MajorId
