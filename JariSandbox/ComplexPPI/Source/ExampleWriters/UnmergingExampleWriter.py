import sys
from SentenceExampleWriter import SentenceExampleWriter
import InteractionXML.IDUtils as IDUtils
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET
import combine

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
        self.entitiesByHeadByType = {}
        #self.tokenByOffset = {}
        #for token in sentenceObject.tokens:
        #    self.tokenByOffset[token.get("charOffset")] = token
        #    self.entityByHeadByType[token.get("charOffset")] = {}
        for entity in sentenceObject.entities:
            # by offset
            offset = entity.get("headOffset")
            if not self.entitiesByHeadByType.has_key(offset):
                self.entitiesByHeadByType[offset] = {}
            # by type
            eType = entity.get("type")
            if entity.get("isName") != "True":
                self.entitiesByHeadByType[offset][eType] = []
            else: # add names to structure
                if not self.entitiesByHeadByType[offset].has_key(eType):
                    self.entitiesByHeadByType[offset][eType] = []
                self.entitiesByHeadByType[offset][eType].append(entity)
        
        entityKeys = sentenceObject.entitiesById.keys()
        exampleByEntityId = {}
        for example in examples:
            #if predictionsByExample[example[0]][0] == 1: # negative
            #    continue
            eId = example[3]["e"]
            assert eId in entityKeys
            if not exampleByEntityId.has_key(eId):
                exampleByEntityId[eId] = []
            exampleByEntityId[eId].append(example)
        
        # This doesn't work, it was an attempt to include
        # only the positive example with the highest prediction strength
#        for key in sorted(exampleByEntityId.keys()):
#            eType = sentenceObject.entitiesById[key].get("type")
#            eExamples = exampleByEntityId[key]
#            if eType == "Binding" and len(eExamples) > 1:
#                maxArgs = -1
#                maxStr = -999999999
#                for example in eExamples:
#                    if predictionsByExample[example[0]][0] == 1:
#                        continue
#                    numArgs = example[3]["i"].count(",") + 1
#                    if numArgs > maxArgs:
#                        maxArgs = numArgs
#                    predClass = predictionsByExample[example[0]][0]
#                    predictionStrength = predictionsByExample[example[0]][predClass]
#                    if predictionStrength > maxStr:
#                        maxStr = predictionStrength
#                #print maxArgs, len(eExamples)
#                for example in eExamples:
#                    if predictionsByExample[example[0]][0] == 1:
#                        continue
#                    predClass = predictionsByExample[example[0]][0]
#                    predictionStrength = predictionsByExample[example[0]][predClass]
#                    if predictionStrength != maxStr:
#                        examples.remove(example)
#                    #if example[3]["i"].count(",") + 1 < maxArgs:
#                    #    examples.remove(example)
        
        #self.newEntitiesById = {}
        #self.outEdgesByEntity = {}
        
        # Gather arguments for the simple, one-argument events
        argumentsByExample = {}
        positiveExamples = []
        exampleIdCount = 0
        for entity in entities:
            # If no example, case is unambiguous
            if not exampleByEntityId.has_key(entity.get("id")):
                simpleEventInteractions = interactionsByEntity[entity.get("id")]
                numCauses = 0
                numThemes = 0
                for interaction in simpleEventInteractions[:]:
                    if self.isIntersentence(interaction):
                        print "Warning, intersentence interaction for", entity.get("id"), entity.get("type")
                        simpleEventInteractions.remove(interaction)
                        continue
                    if interaction.get("type") == "neg":
                        simpleEventInteractions.remove(interaction)
                        continue
                    iType = interaction.get("type")
                    if iType == "Cause":
                        numCauses += 1
                    elif iType == "Theme":
                        numThemes += 1
                eType = entity.get("type")
                assert numThemes == 0 or (numThemes != 0 and numCauses == 0) or (numThemes > 1 and eType != "Binding"), (numThemes,numCauses,eType,entity.get("id"))
                #assert numThemes == 0 or (numThemes != 0 and numCauses == 0) or (numThemes > 1 and eType == "Binding"), (numThemes,numCauses,eType,entity.get("id"))
                for interaction in simpleEventInteractions:
                    exampleId = "simple." + str(exampleIdCount)
                    exampleIdCount += 1
                    positiveExamples.append([exampleId,None,None,None])
                    argumentsByExample[exampleId] = [interaction]
                    #self.addEvent([interaction], sentenceObject, "simple")
            
        # Gather arguments for predicted, unmerged events
        for example in examples:
            #print predictionsByExample[example[0]]
            if predictionsByExample[example[0]][0] == 1: # negative
                continue
            positiveExamples.append(example)
            arguments = []
            for iId in example[3]["i"].split(","):
                arg = interactionsById[iId]
                if self.isIntersentence(arg):
                    continue
                assert arg.get("type") != "neg"
                arguments.append(arg)
            argumentsByExample[example[0]] = arguments
        
        # Loop until all positive examples are added
        examplesLeft = len(positiveExamples)
        exampleAdded = {}
        for example in positiveExamples:
            exampleAdded[example[0]] = False
        forceAdd = False
        while examplesLeft > 0:
            examplesAddedThisRound = 0
            for example in positiveExamples:
                if exampleAdded[example[0]]:
                    continue
                arguments = argumentsByExample[example[0]]
                if forceAdd or self.argumentEntitiesExist(arguments, sentenceObject):
                    umType = "complex"
                    predictionStrength = None
                    if example[0].find("simple") != -1:
                        umType = "simple"
                    else:
                        predictionStrength = self.getPredictionStrength(example, predictionsByExample)
                    self.addEvent(arguments, sentenceObject, umType, forceAdd, predictionStrength)
                    exampleAdded[example[0]] = True
                    examplesLeft -= 1
                    examplesAddedThisRound += 1
                    forceAdd = False
            if examplesLeft > 0 and examplesAddedThisRound == 0:
                print "Warning, forcing event addition"
                forceAdd = True                  
        
        # Attach the new elements
        for element in self.newEntities + self.newInteractions:
            sentenceElement.append(element)

        # re-attach the analyses-element
        if sentenceAnalysesElement != None:
            sentenceElement.append(sentenceAnalysesElement)
    
    def argumentEntitiesExist(self, arguments, sentenceObject):
        for arg in arguments:
            e2Id = arg.get("e2")
            origE2 = sentenceObject.entitiesById[e2Id]
            e2HeadOffset = origE2.get("headOffset")
            e2Type = origE2.get("type")
            if len(self.entitiesByHeadByType[e2HeadOffset][e2Type]) == 0:
                return False
        return True
    
    def addEvent(self, arguments, sentenceObject, umType="unknown", forceAdd=False, predictionStrength=None):
        # Collect e2 entities linked by this event
        e1Id = None
        argEntities = [[]] * (len(arguments))
        for i in range(len(arguments)):
            arg = arguments[i]
            argE1Id = arg.get("e1")
            if e1Id != None:
                assert e1Id == argE1Id
            else:
                e1Id = argE1Id
                origE1 = sentenceObject.entitiesById[argE1Id]
            
            e2Id = arg.get("e2")
            origE2 = sentenceObject.entitiesById[e2Id]
            e2HeadOffset = origE2.get("headOffset")
            e2Type = origE2.get("type")
            argEntities[i] = self.entitiesByHeadByType[e2HeadOffset][e2Type]
            if len(argEntities[i]) == 0:
                assert forceAdd
                argEntities[i] = [self.addEntity(origE2)]
            
        entityCombinations = combine.combine(*argEntities)
        for combination in entityCombinations:
            root = self.addEntity(origE1)
            root.set("umType", umType)
            if predictionStrength != None:
                root.set("umStrength", str(predictionStrength))
            for i in range(len(arguments)):
                self.addInteraction(root, combination[i], arguments[i])
    
    def addEntity(self, entity):
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
        # Add to dictionary
        eType = entityElement.get("type")
        headOffset = entityElement.get("headOffset")
        if not self.entitiesByHeadByType[headOffset].has_key(eType):
            self.entitiesByHeadByType[headOffset][eType] = []
        self.entitiesByHeadByType[headOffset][eType].append(entityElement)
        self.newEntities.append(entityElement)
        self.entityCount += 1
        
        return entityElement
    
    def addInteraction(self, e1, e2, arg):
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

        return interactionElement
    
    def isIntersentence(self, interaction):
        e1MajorId, e1MinorId = interaction.get("e1").rsplit(".e", 1)
        e2MajorId, e2MinorId = interaction.get("e2").rsplit(".e", 1)
        return e1MajorId != e2MajorId
    
    def getPredictionStrength(self, example, predictionsByExample):
        prediction = predictionsByExample[example[0]]
        if len(prediction) == 1:
            return 0
        predClass = prediction[0]
        predictionStrength = [predClass]
        return predictionStrength










class UnmergingExampleWriterOld(SentenceExampleWriter):
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
                        for rootEntity in self.insertEvent([interaction], sentenceObject):
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
            for rootEntity in self.insertEvent(arguments, sentenceObject):
            #if rootEntity != None:
                rootEntity.set("umType", "complex")
        
        # Attach the new elements
        for element in self.newEntities + self.newInteractions:
            sentenceElement.append(element)

        # re-attach the analyses-element
        if sentenceAnalysesElement != None:
            sentenceElement.append(sentenceAnalysesElement)
    
    def insertEvent(self, arguments, sentenceObject):
        currentEntities = {} # Entities being part of the current event
        rootEntities = []

        for arg in arguments:
            e1s = []
            e2s = []
            
            e1Id = arg.get("e1")
            e2Id = arg.get("e2")
            # E1
            origE1 = sentenceObject.entitiesById[e1Id]
            e1HeadOffset = origE1.get("headOffset")
            e1Type = origE1.get("type")
            if e1Id not in currentEntities.keys():
                #e1 = None
                if self.entityByHeadByType[e1HeadOffset].has_key(e1Type):
                    for entity in self.entityByHeadByType[e1HeadOffset][e1Type]:
                        if not self.outEdgesByEntity.has_key(entity):
                            #e1 = entity
                            e1s.append(entity)
                            #currentEntities[e1Id] = entity
                            #break
                if len(e1s) == 0:
                    entity = self.insertEntity(sentenceObject.entitiesById[e1Id])
                    e1s.append( entity )
                    currentEntities[e1Id] = entity
            else:
                e1s.append( currentEntities[e1Id] )
            
            #if rootEntity == None:
            #    rootEntity = e1
            #else:
            #    assert rootEntity == e1
            # E2
            assert e2Id in sentenceObject.entitiesById.keys(), self.sentenceId + "/" + e2Id
            origE2 = sentenceObject.entitiesById[e2Id]
            e2HeadOffset = origE2.get("headOffset")
            e2Type = origE2.get("type")
            if e2Id not in currentEntities.keys():
                if self.entityByHeadByType[e2HeadOffset].has_key(e2Type):
                    for entity in self.entityByHeadByType[e2HeadOffset][e2Type]:
                        e2s.append(entity)
                    #e2 = self.entityByHeadByType[e2HeadOffset][e2Type][0]
                else:
                    entity = self.insertEntity(sentenceObject.entitiesById[e2Id]) 
                    e2s.append(entity)
                    currentEntities[e2Id] = entity
            else:
                e2s.append( currentEntities[e2Id] )
        
            assert len(e1s) > 0
            assert len(e2s) > 0
            for e1 in e1s:
                rootEntities.append(e1)
            for entityCombination in combine.combine(e1s, e2s):
            #self.insertInteraction(e1, e2, arg)
                self.insertInteraction(entityCombination[0], entityCombination[1], arg)
        return rootEntities #rootEntity
    
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
