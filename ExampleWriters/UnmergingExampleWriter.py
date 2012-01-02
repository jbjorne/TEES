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
        SentenceExampleWriter.__init__(self)
    
    def writeXMLSentence(self, examples, predictionsByExample, sentenceObject, classSet, classIds, goldSentence=None):        
        sentenceElement = sentenceObject.sentence
        self.sentenceId = sentenceElement.get("id")
        self.assertSameSentence(examples, self.sentenceId)
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
            if entity.get("id") not in exampleByEntityId:
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
                assert numThemes == 0 or (numThemes != 0 and numCauses == 0) or (numThemes > 1 and eType != "Binding"), (numThemes,numCauses,eType,entity.get("id"), [x[0] for x in examples], entityKeys)
                #assert numThemes == 0 or (numThemes != 0 and numCauses == 0) or (numThemes > 1 and eType == "Binding"), (numThemes,numCauses,eType,entity.get("id"))
                for interaction in simpleEventInteractions:
                    self.counts["simple-" + eType + "-" + interaction.get("type")] += 1
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
                if iId == "": # processes can have 0 arguments
                    assert "etype" in example[3], example[3]
                    assert example[3]["etype"] == "Process", example[3]
                    break
                arg = interactionsById[iId]
                if self.isIntersentence(arg):
                    continue
                assert arg.get("type") != "neg"
                arguments.append(arg)
            argumentsByExample[example[0]] = arguments
        
        # Loop until all positive examples are added. This process
        # assumes that the events (mostly) form a directed acyclic
        # graph, which can written by "growing" the structure from
        # the "leaf" events, and consecutively adding levels of
        # nesting events.
        examplesLeft = len(positiveExamples)
        exampleAdded = {}
        for example in positiveExamples:
            exampleAdded[example[0]] = False
        forceAdd = False
        forcedCount = 0
        while examplesLeft > 0:
            examplesAddedThisRound = 0
            # For each round, loop through the potentially remaining examples
            for example in positiveExamples:
                if exampleAdded[example[0]]: # This event has already been inserted
                    continue
                arguments = argumentsByExample[example[0]]
                # An event can be added if all of its argument events have already
                # been added. Addition is forced if lack of argument events blocks
                # the process.
                if forceAdd or self.argumentEntitiesExist(arguments, sentenceObject):
                    umType = "complex" # mark the root entity in the output xml
                    predictionStrength = None
                    if example[0].find("simple") != -1:
                        umType = "simple"
                    else:
                        # Prediction strength is only available for classified argument groups
                        predictionStrength = self.getPredictionStrength(example, predictionsByExample, classSet, classIds)
                    #print example 
                    if umType != "simple" and example[3]["etype"] == "Process" and len(arguments) == 0:
                        origProcess = sentenceObject.entitiesById[example[3]["e"]]
                        # Put back the original entity
                        newProcess = self.addEntity(origProcess)
                        newProcess.set("umType", umType)
                        if predictionStrength != None:
                            newProcess.set("umStrength", str(predictionStrength))
                    else: # example has arguments
                        self.addEvent(arguments, sentenceObject, umType, forceAdd, predictionStrength)
                    exampleAdded[example[0]] = True
                    examplesLeft -= 1
                    examplesAddedThisRound += 1
                    forceAdd = False
            if examplesLeft > 0 and examplesAddedThisRound == 0:
                # If there are examples left, but nothing was added, this
                # means that some nested events are missing. Theoretically
                # this could also be because two events are referring to
                # each other, preventing each other's insertion. In any
                # case this is solved by simply forcing the addition of 
                # the first non-inserted event, by creating 0-argument
                # entities for its argument events.
                forcedCount += 1
                #print "Warning, forcing event addition"
                forceAdd = True                  
        
        # Attach the new elements
        for element in self.newEntities + self.newInteractions:
            sentenceElement.append(element)

        # re-attach the analyses-element
        if sentenceAnalysesElement != None:
            sentenceElement.append(sentenceAnalysesElement)
        
        #print "Warning, forced addition of", forcedCount, "events"
    
    def argumentEntitiesExist(self, arguments, sentenceObject):
        """
        Checks whether entity elements have already been created 
        for the argument entities, i.e. whether the argument events
        have been inserted.
        """
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
            # Take the entity trigger node from the e1 attribute of the argument
            if e1Id != None: # trigger has already been found
                assert e1Id == argE1Id
            else: # find the trigger
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
    
    def getPredictionStrength(self, example, predictionsByExample, classSet, classIds):
        prediction = predictionsByExample[example[0]]
        if len(prediction) == 1:
            return 0
        predClass = prediction[0]
        #predictionStrength = [predClass]
        predictionStrength = self.getPredictionStrengthString(prediction, classSet, classIds)
        return predictionStrength