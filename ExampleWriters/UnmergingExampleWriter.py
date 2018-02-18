import sys
from SentenceExampleWriter import SentenceExampleWriter
import Utils.InteractionXML.IDUtils as IDUtils
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET
import Utils.Libraries.combine as combine

class UnmergingExampleWriter(SentenceExampleWriter):
    def __init__(self):
        self.xType = "um"
        SentenceExampleWriter.__init__(self)
        
    def getInteractionsAndRelations(self, interactions):
        # filter interactions
        interactionsToKeep = []
        relations = []
        for interaction in interactions:
            if interaction.get("type") != "neg":
                interactionsToKeep.append(interaction)
            if interaction.get("event") != "True":
                relations.append(interaction)
        return interactionsToKeep, relations
    
    def mapInteractions(self, interactions, entities):
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
        return interactionsByEntity, interactionsById
    
    def mapEntities(self, entities):
        # Mapping for connecting the events
        self.entitiesByHeadByType = {}
        for entity in entities:
            # by offset
            offset = entity.get("headOffset")
            if not self.entitiesByHeadByType.has_key(offset):
                self.entitiesByHeadByType[offset] = {}
            # by type
            eType = entity.get("type")
            if entity.get("given") != "True":
                self.entitiesByHeadByType[offset][eType] = []
            else: # add names to structure
                if not self.entitiesByHeadByType[offset].has_key(eType):
                    self.entitiesByHeadByType[offset][eType] = []
                self.entitiesByHeadByType[offset][eType].append(entity)
    
    def mapEntityDuplicates(self, entities):
        self.entityToDuplicates = {}
        for e1 in entities:
            e1Id = e1.get("id")
            for e2 in entities:
                if e1.get("type") == e2.get("type") and e1.get("headOffset") == e2.get("headOffset"):
                    if e1Id not in self.entityToDuplicates:
                        self.entityToDuplicates[e1Id] = set()
                    self.entityToDuplicates[e1Id].add(e2.get("id"))
    
    def mapExamples(self, examples, sentenceObject):
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
        return exampleByEntityId
    
    def isPredictionNegative(self, prediction):
        if isinstance(prediction, dict):
            encoded = prediction["prediction"]
            if len([x for x in encoded if x == 1]) == 0: # negative
                return True 
        elif prediction[0] == 1: # negative
            return True
        else:
            return False
    
    def connectArgumentsToExamples(self, examples, predictionsByExample, interactionsById, entityById):
        # Gather arguments for predicted, unmerged events
        argumentsByExample = {}
        for example in examples:
            # Check for negatives
            if self.isPredictionNegative(predictionsByExample[example[0]]):
                continue
            # Get the arguments
            arguments = []
            for iId in example[3]["i"].split(","):
                if iId == "": # For example Process events can have 0 arguments
                    break
                argType, iId = iId.split("=")
                arg = interactionsById[iId]
                if self.isIntersentence(arg, entityById):
                    continue
                assert arg.get("type") != "neg"
                arguments.append(arg)
            argumentsByExample[example[0]] = arguments
        return argumentsByExample
    
    def insertRelations(self, relations, entityById):
        for relation in relations:
            e1Id = relation.get("e1")
            e2Id = relation.get("e2")
            if e2Id not in entityById: # intersentence relation, skip
                continue
            origE1 = entityById[e1Id]
            origE2 = entityById[e2Id]
            e1Type = origE1.get("type")
            e1Offset = origE1.get("headOffset")
            e2Type = origE2.get("type")
            e2Offset = origE2.get("headOffset")
            
            for e1 in self.entitiesByHeadByType[e1Offset][e1Type]:
                for e2 in self.entitiesByHeadByType[e2Offset][e2Type]:
                    self.addInteraction(e1, e2, relation)
    
    def insertExamples(self, examples, predictionsByExample, argumentsByExample, sentenceObject, classSet, classIds, cutoff=100):
        positiveExamples = []
        for example in examples:
            if self.isPredictionNegative(predictionsByExample[example[0]]): #predictionsByExample[example[0]][0] == 1: # negative
                continue
            positiveExamples.append(example)
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
            if len(self.newEntities) > cutoff:
                print >> sys.stderr, "Warning, sentence", sentenceObject.sentence.get("id"), "has generated more than", cutoff, "events, skipping the rest."
                break
            examplesAddedThisRound = 0
            # For each round, loop through the potentially remaining examples
            for example in positiveExamples:
                if len(self.newEntities) > cutoff:
                    print >> sys.stderr, "Warning, sentence", sentenceObject.sentence.get("id"), "has generated more than", cutoff, "entities, skipping the rest."
                    break
                if exampleAdded[example[0]]: # This event has already been inserted
                    continue
                arguments = argumentsByExample[example[0]]
                # An event can be added if all of its argument events have already
                # been added. Addition is forced if lack of argument events blocks
                # the process.
                if forceAdd or self.argumentEntitiesExist(arguments, sentenceObject):
                    predictionStrength = self.getPredictionStrength(example, predictionsByExample, classSet, classIds)
                    self.addEvent(example, arguments, sentenceObject, forceAdd, predictionStrength, exampleNotes=example[3])
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
                #forcedCount += 1
                #forceAdd = True
                
                # skip the rest, as the structure will be invalid anyway
                examplesLeft = 0 

    def writeXMLSentence(self, examples, predictionsByExample, sentenceObject, classSet, classIds, goldSentence=None, exampleStyle=None, structureAnalyzer=None):        
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
        interactions = self.removeChildren(sentenceElement, ["interaction"])
        arguments, relations = self.getInteractionsAndRelations(interactions)
        # remove entities
        entities = self.removeNonNameEntities(sentenceElement)
        interactionsByEntity, interactionsById = self.mapInteractions(arguments + relations, sentenceObject.entities)

        self.entityCount = IDUtils.getNextFreeId(sentenceElement.findall("entity"))
        self.interactionCount = IDUtils.getNextFreeId(sentenceElement.findall("interaction"))
        self.newEntities = []
        self.newInteractions = []
        
        self.mapEntities(sentenceObject.entities)
        exampleByEntityId = self.mapExamples(examples, sentenceObject)
        argumentsByExample = self.connectArgumentsToExamples(examples, predictionsByExample, interactionsById, sentenceObject.entitiesById)
        self.mapEntityDuplicates(sentenceObject.entities)
        
        self.insertExamples(examples, predictionsByExample, argumentsByExample, sentenceObject, classSet, classIds)
        self.insertRelations(relations, sentenceObject.entitiesById)
        
        # Attach the new elements
        for element in self.newEntities + self.newInteractions:
            sentenceElement.append(element)

        # re-attach the analyses-element
        if sentenceAnalysesElement != None:
            sentenceElement.append(sentenceAnalysesElement)
        
        










        
        
        
        
        

    
#    def writeXMLSentenceOld(self, examples, predictionsByExample, sentenceObject, classSet, classIds, goldSentence=None, exampleStyle=None):        
#        sentenceElement = sentenceObject.sentence
#        self.sentenceId = sentenceElement.get("id")
#        self.assertSameSentence(examples, self.sentenceId)
#        # detach analyses-element
#        sentenceAnalysesElement = None
#        sentenceAnalysesElement = sentenceElement.find("sentenceanalyses")
#        if sentenceAnalysesElement == None:
#            sentenceAnalysesElement = sentenceElement.find("analyses")
#        if sentenceAnalysesElement != None:
#            sentenceElement.remove(sentenceAnalysesElement)
#                
#        # remove pairs and interactions
#        interactions = self.removeChildren(sentenceElement, ["pair", "interaction"])
#        # remove entities
#        entities = self.removeNonNameEntities(sentenceElement)
#        
#        # filter interactions
#        interactionsToKeep = []
#        for interaction in interactions:
#            if interaction.get("type") != "neg":
#                interactionsToKeep.append(interaction)
#        interactions = interactionsToKeep
#        
#        # early out
#        cutoff = 100
#        #if len(interactions) == 0 or len(interactions) > cutoff:
#        if len(interactions) > cutoff:
#            # re-attach the analyses-element
#            if sentenceAnalysesElement != None:
#                sentenceElement.append(sentenceAnalysesElement)
#            #if len(interactions) > cutoff:
#            print >> sys.stderr, "Warning, sentence", sentenceObject.sentence.get("id"), "has more than", cutoff, "interactions, removing all."
#            return
#        
#        interactionsByEntity = {}
#        interactionsById = {}
#        for entity in entities:
#            interactionsByEntity[entity.get("id")] = []
#        for interaction in interactions:
#            e1Id = interaction.get("e1")
#            if not interactionsByEntity.has_key(e1Id):
#                interactionsByEntity[e1Id] = []
#            interactionsByEntity[e1Id].append(interaction)
#            interactionsById[interaction.get("id")] = interaction
#
#        # NOTE! Following won't work for pairs
#        self.entityCount = IDUtils.getNextFreeId(sentenceElement.findall("entity"))
#        self.interactionCount = IDUtils.getNextFreeId(sentenceElement.findall("interaction"))
#        self.newEntities = []
#        self.newInteractions = []
#        
#        # Mapping for connecting the events
#        self.entitiesByHeadByType = {}
#        #self.tokenByOffset = {}
#        #for token in sentenceObject.tokens:
#        #    self.tokenByOffset[token.get("charOffset")] = token
#        #    self.entityByHeadByType[token.get("charOffset")] = {}
#        for entity in sentenceObject.entities:
#            # by offset
#            offset = entity.get("headOffset")
#            if not self.entitiesByHeadByType.has_key(offset):
#                self.entitiesByHeadByType[offset] = {}
#            # by type
#            eType = entity.get("type")
#            if entity.get("given") != "True":
#                self.entitiesByHeadByType[offset][eType] = []
#            else: # add names to structure
#                if not self.entitiesByHeadByType[offset].has_key(eType):
#                    self.entitiesByHeadByType[offset][eType] = []
#                self.entitiesByHeadByType[offset][eType].append(entity)
#        
#        entityKeys = sentenceObject.entitiesById.keys()
#        exampleByEntityId = {}
#        for example in examples:
#            #if predictionsByExample[example[0]][0] == 1: # negative
#            #    continue
#            eId = example[3]["e"]
#            assert eId in entityKeys
#            if not exampleByEntityId.has_key(eId):
#                exampleByEntityId[eId] = []
#            exampleByEntityId[eId].append(example)
#        
#        # This doesn't work, it was an attempt to include
#        # only the positive example with the highest prediction strength
##        for key in sorted(exampleByEntityId.keys()):
##            eType = sentenceObject.entitiesById[key].get("type")
##            eExamples = exampleByEntityId[key]
##            if eType == "Binding" and len(eExamples) > 1:
##                maxArgs = -1
##                maxStr = -999999999
##                for example in eExamples:
##                    if predictionsByExample[example[0]][0] == 1:
##                        continue
##                    numArgs = example[3]["i"].count(",") + 1
##                    if numArgs > maxArgs:
##                        maxArgs = numArgs
##                    predClass = predictionsByExample[example[0]][0]
##                    predictionStrength = predictionsByExample[example[0]][predClass]
##                    if predictionStrength > maxStr:
##                        maxStr = predictionStrength
##                #print maxArgs, len(eExamples)
##                for example in eExamples:
##                    if predictionsByExample[example[0]][0] == 1:
##                        continue
##                    predClass = predictionsByExample[example[0]][0]
##                    predictionStrength = predictionsByExample[example[0]][predClass]
##                    if predictionStrength != maxStr:
##                        examples.remove(example)
##                    #if example[3]["i"].count(",") + 1 < maxArgs:
##                    #    examples.remove(example)
#        
#        #self.newEntitiesById = {}
#        #self.outEdgesByEntity = {}
#        
#        # Gather arguments for the simple, one-argument events
#        argumentsByExample = {}
#        positiveExamples = []
#        exampleIdCount = 0
#        for entity in entities:
#            # If no example, case is unambiguous
#            if entity.get("id") not in exampleByEntityId:
#                simpleEventInteractions = interactionsByEntity[entity.get("id")]
#                numCauses = 0
#                numThemes = 0
#                for interaction in simpleEventInteractions[:]:
#                    if self.isIntersentence(interaction):
#                        print "Warning, intersentence interaction for", entity.get("id"), entity.get("type")
#                        simpleEventInteractions.remove(interaction)
#                        continue
#                    if interaction.get("type") == "neg":
#                        simpleEventInteractions.remove(interaction)
#                        continue
#                    iType = interaction.get("type")
#                    if iType == "Cause":
#                        numCauses += 1
#                    elif iType == "Theme":
#                        numThemes += 1
#                eType = entity.get("type")
#                assert numThemes == 0 or (numThemes != 0 and numCauses == 0) or (numThemes > 1 and eType != "Binding"), (numThemes,numCauses,eType,entity.get("id"), [x[0] for x in examples], entityKeys)
#                #assert numThemes == 0 or (numThemes != 0 and numCauses == 0) or (numThemes > 1 and eType == "Binding"), (numThemes,numCauses,eType,entity.get("id"))
#                for interaction in simpleEventInteractions:
#                    self.counts["simple-" + eType + "-" + interaction.get("type")] += 1
#                    exampleId = "simple." + str(exampleIdCount)
#                    exampleIdCount += 1
#                    positiveExamples.append([exampleId,None,None,None])
#                    argumentsByExample[exampleId] = [interaction]
#                    #self.addEvent([interaction], sentenceObject, "simple")
#            
#        # Gather arguments for predicted, unmerged events
#        for example in examples:
#            #print predictionsByExample[example[0]]
#            if predictionsByExample[example[0]][0] == 1: # negative
#                continue
#            positiveExamples.append(example)
#            arguments = []
#            for iId in example[3]["i"].split(","):
#                if iId == "": # processes can have 0 arguments
#                    assert "etype" in example[3], example[3]
#                    assert example[3]["etype"] == "Process", example[3]
#                    break
#                arg = interactionsById[iId]
#                if self.isIntersentence(arg):
#                    continue
#                assert arg.get("type") != "neg"
#                arguments.append(arg)
#            argumentsByExample[example[0]] = arguments
#        
#        # Loop until all positive examples are added. This process
#        # assumes that the events (mostly) form a directed acyclic
#        # graph, which can written by "growing" the structure from
#        # the "leaf" events, and consecutively adding levels of
#        # nesting events.
#        examplesLeft = len(positiveExamples)
#        exampleAdded = {}
#        for example in positiveExamples:
#            exampleAdded[example[0]] = False
#        forceAdd = False
#        forcedCount = 0
#        while examplesLeft > 0:
#            if len(self.newEntities) > 100:
#                print >> sys.stderr, "Warning, sentence", sentenceObject.sentence.get("id"), "has generated more than", cutoff, "events, skipping the rest."
#                break
#            examplesAddedThisRound = 0
#            # For each round, loop through the potentially remaining examples
#            for example in positiveExamples:
#                if len(self.newEntities) > 100:
#                    break
#                if exampleAdded[example[0]]: # This event has already been inserted
#                    continue
#                arguments = argumentsByExample[example[0]]
#                # An event can be added if all of its argument events have already
#                # been added. Addition is forced if lack of argument events blocks
#                # the process.
#                if forceAdd or self.argumentEntitiesExist(arguments, sentenceObject):
#                    umType = "complex" # mark the root entity in the output xml
#                    predictionStrength = None
#                    if example[0].find("simple") != -1:
#                        umType = "simple"
#                    else:
#                        # Prediction strength is only available for classified argument groups
#                        predictionStrength = self.getPredictionStrength(example, predictionsByExample, classSet, classIds)
#                    #print example 
#                    if umType != "simple" and "etype" in example[3] and example[3]["etype"] == "Process" and len(arguments) == 0:
#                        origProcess = sentenceObject.entitiesById[example[3]["e"]]
#                        # Put back the original entity
#                        newProcess = self.addEntity(origProcess)
#                        newProcess.set("umType", umType)
#                        if predictionStrength != None:
#                            newProcess.set("umStrength", str(predictionStrength))
#                    else: # example has arguments
#                        self.addEvent(arguments, sentenceObject, umType, forceAdd, predictionStrength, exampleNotes=example[3])
#                    exampleAdded[example[0]] = True
#                    examplesLeft -= 1
#                    examplesAddedThisRound += 1
#                    forceAdd = False
#            if examplesLeft > 0 and examplesAddedThisRound == 0:
#                # If there are examples left, but nothing was added, this
#                # means that some nested events are missing. Theoretically
#                # this could also be because two events are referring to
#                # each other, preventing each other's insertion. In any
#                # case this is solved by simply forcing the addition of 
#                # the first non-inserted event, by creating 0-argument
#                # entities for its argument events.
#                forcedCount += 1
#                #print "Warning, forcing event addition"
#                forceAdd = True                  
#        
#        # Attach the new elements
#        for element in self.newEntities + self.newInteractions:
#            sentenceElement.append(element)
#
#        # re-attach the analyses-element
#        if sentenceAnalysesElement != None:
#            sentenceElement.append(sentenceAnalysesElement)
#        
#        #print "Warning, forced addition of", forcedCount, "events"
    
    def argumentEntitiesExist(self, arguments, sentenceObject):
        """
        Checks whether entity elements have already been created 
        for the argument entities, i.e. whether the argument events
        have been inserted.
        """
        for arg in arguments:
            e2Id = arg.get("e2")
            if e2Id not in sentenceObject.entitiesById: # intersentence interaction
                continue
            origE2 = sentenceObject.entitiesById[e2Id]
            e2HeadOffset = origE2.get("headOffset")
            e2Type = origE2.get("type")
            if len(self.entitiesByHeadByType[e2HeadOffset][e2Type]) == 0:
                return False
        return True
    
    def addEvent(self, example, arguments, sentenceObject, forceAdd=False, predictionStrength=None, exampleNotes=None):
        if len(arguments) == 0: # A zero-argument event
            e1Id = example[3]["e"]
            origE1 = sentenceObject.entitiesById[e1Id]
            entityCombinations = [None]
        else:
            # Collect e2 entities linked by this event
            e1Id = None
            origE1 = None
            argEntities = [[]] * (len(arguments))
            for i in range(len(arguments)):
                arg = arguments[i]
                argE1Id = arg.get("e1")
                # Take the entity trigger node from the e1 attribute of the argument
                if e1Id != None: # trigger has already been found
                    assert argE1Id in self.entityToDuplicates[e1Id], ((e1Id, argE1Id), example[3], arguments)
                    #assert e1Id == argE1Id, ((e1Id, argE1Id), example[3], arguments)
                else: # find the trigger (any of the original identical triggers is OK
                    e1Id = argE1Id
                    origE1 = sentenceObject.entitiesById[argE1Id]
                
                e2Id = arg.get("e2")
                if e2Id in sentenceObject.entitiesById:
                    origE2 = sentenceObject.entitiesById[e2Id]
                    e2HeadOffset = origE2.get("headOffset")
                    e2Type = origE2.get("type")
                    argEntities[i] = self.entitiesByHeadByType[e2HeadOffset][e2Type]
                    if len(argEntities[i]) == 0:
                        assert forceAdd
                        if origE2.get("given") != "True":
                            argEntities[i] = [self.addEntity(origE2)]
                        else:
                            argEntities[i] = [origE2]
                else:
                    argEntities[i] = ["INTERSENTENCE"]
            entityCombinations = combine.combine(*argEntities)
        
        for combination in entityCombinations:
            assert origE1 != None, (sentenceObject.sentence.get("id"), exampleNotes, [(x.get("id"), x.get("e1"), x.get("e2")) for x in arguments])
            root = self.addEntity(origE1)
            if predictionStrength != None:
                root.set("umConf", str(predictionStrength))
            for i in range(len(arguments)):
                self.addInteraction(root, combination[i], arguments[i])
    
    def addEntity(self, entity):
        entityElement = ET.Element("entity")
        assert entity.get("given") != "True", entity.attrib
        for key in entity.attrib.keys(): # copy from template
            entityElement.set(key, entity.get(key))
        entityElement.set("id", self.sentenceId + ".e" + str(self.entityCount))
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
        for key in arg.attrib.keys(): # copy from template
            interactionElement.set(key, arg.get(key))
        interactionElement.set("e1", e1.get("id"))
        if e2 == "INTERSENTENCE":
            interactionElement.set("e2", arg.get("e2")) # preserve original id
        else:
            interactionElement.set("e2", e2.get("id"))
        interactionElement.set("id", self.sentenceId + ".i" + str(self.interactionCount))
        self.newInteractions.append(interactionElement)
        self.interactionCount += 1

        return interactionElement
    
    def isIntersentence(self, interaction, entityById):
        if interaction.get("e1") not in entityById or interaction.get("e2") not in entityById:
            return True
        else:
            return False
        #e1MajorId, e1MinorId = interaction.get("e1").rsplit(".e", 1)
        #e2MajorId, e2MinorId = interaction.get("e2").rsplit(".e", 1)
        #return e1MajorId != e2MajorId
    
    def getPredictionStrength(self, example, predictionsByExample, classSet, classIds):
        prediction = predictionsByExample[example[0]]
        if len(prediction) == 1:
            return 0
        #predClass = prediction[0]
        #predictionStrength = [predClass]
        predictionStrength = self.getPredictionStrengthString(prediction, classSet, classIds)
        return predictionStrength