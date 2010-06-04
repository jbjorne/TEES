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
        
        entityKeys = sentenceObject.entitiesById.keys()
        exampleByEntityId = {}
        for example in examples:
            eId = example[3]["e"]
            assert eId in entityKeys
            exampleByEntityId[eId] = example
        
        self.newEntitiesById = {}
        
        # Add the simple, one-argument events
        for entity in entities:
            # If no example, case is unambiguous
            if not exampleByEntityId.has_key(entity.get("id")):
                for interaction in interactionsByEntity[entity.get("id")]:
                    if self.isIntersentence(interaction):
                        print "Warning, intersentence interaction for", entity.get("id"), entity.get("type")
                        continue
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
            if e1Id not in currentEntities.keys():
                #if self.newEntitiesById.has_key(e1Id):
                #    e1 = self.newEntitiesById[e1Id]
                #else:
                e1 = self.insertEntity(sentenceObject.entitiesById[e1Id])
                self.newEntitiesById[e1Id] = e1
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
            if e2Id not in currentEntities.keys():
                if origE2.get("isName") != "True":
                    if self.newEntitiesById.has_key(e2Id):
                        e2 = self.newEntitiesById[e2Id]
                    else:
                        e2 = self.insertEntity(sentenceObject.entitiesById[e2Id])
                        self.newEntitiesById[e2Id] = e2
                    currentEntities[e2Id] = e2
                else:
                    e2 = origE2
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
        return entityElement
    
    def insertInteraction(self, e1, e2, arg):
        interactionElement = ET.Element("interaction")
        interactionElement.attrib["directed"] = "Unknown"
        interactionElement.attrib["e1"] = e1.get("id")
        interactionElement.attrib["e2"] = e2.get("id")
        interactionElement.attrib["id"] = self.sentenceId + ".i" + str(self.interactionCount)
        interactionElement.set("type", arg.get("type"))
        if arg.get("predictions") != None:
            intElement.set("predictions", arg.get("predictions"))
        self.newInteractions.append(interactionElement)
        self.interactionCount += 1
        return interactionElement
    
    def isIntersentence(self, interaction):
        e1MajorId, e1MinorId = interaction.get("e1").rsplit(".e", 1)
        e2MajorId, e2MinorId = interaction.get("e2").rsplit(".e", 1)
        return e1MajorId != e2MajorId
