import sys, os
import shutil
import gzip
import json
import itertools
import types
from Detector import Detector
from Core.SentenceGraph import getCorpusIterator
import Utils.ElementTreeUtils as ETUtils
from Core.IdSet import IdSet
import Utils.Parameters
import Utils.Settings as Settings
from Utils.EmbeddingIndex import EmbeddingIndex
from Utils.ProgressCounter import ProgressCounter
from ExampleBuilders.ExampleStats import ExampleStats
from Evaluators import EvaluateInteractionXML
from Utils import Parameters
from ExampleWriters.UnmergingExampleWriter import UnmergingExampleWriter
from Evaluators.AveragingMultiClassEvaluator import AveragingMultiClassEvaluator
import Utils.InteractionXML.InteractionXMLUtils as IXMLUtils
import numpy
from keras.layers import Dense
from keras.models import Model, load_model
from keras.layers.core import Dropout, Flatten
from keras.optimizers import Adam
from keras.callbacks import EarlyStopping, ModelCheckpoint
from keras.layers import merge
from itertools import chain
import sklearn.metrics
from sklearn.preprocessing.label import MultiLabelBinarizer
from sklearn.metrics.classification import classification_report
from keras.layers import Conv1D
from keras.layers.pooling import MaxPooling1D
from __builtin__ import isinstance
from Detectors.KerasDetectorBase import KerasDetectorBase
import Utils.Range as Range
from collections import defaultdict
import Utils.Libraries.combine as combine

def combinations(iterable, r):
    # combinations('ABCD', 2) --> AB AC AD BC BD CD
    # combinations(range(4), 3) --> 012 013 023 123
    pool = tuple(iterable)
    n = len(pool)
    if r > n:
        return
    indices = range(r)
    yield tuple(pool[i] for i in indices)
    while True:
        for i in reversed(range(r)):
            if indices[i] != i + n - r:
                break
        else:
            return
        indices[i] += 1
        for j in range(i+1, r):
            indices[j] = indices[j-1] + 1
        yield tuple(pool[i] for i in indices)

def compareInteractionPrecedence(e1, e2):
    """
    e1/e2 = (interaction, pathdist, lindist, tok2pos)
    """
    if e1[1] > e2[1]:
        return 1
    elif e1[1] < e2[1]:
        return -1
    else: # same dependency distance
        if e1[2] > e2[2]:
            return 1
        elif e1[2] < e2[2]:
            return -1
        else: # same linear distance
            if e1[3] > e2[3]:
                return 1
            elif e1[3] < e2[3]:
                return -1
            else: # same head token for entity 2
                return 0
                #assert False, ("Precedence error",e1,e2)

class KerasUnmergingDetector(KerasDetectorBase):

    def __init__(self):
        KerasDetectorBase.__init__(self)
        self.tag = "unmerging-"
        self.exampleWriter = UnmergingExampleWriter()
        self.useSeparateGold = True
        self.defaultStyles = {"keep_intersentence_gold":True}

    ###########################################################################
    # Example Generation
    ###########################################################################
    
    def processDocument(self, sentences, goldSentences, examples):
        if "keep_intersentence_gold" not in self.styles:
            self.styles["keep_intersentence_gold"] = True
        
        self.documentEntitiesById = {}
        for sentence in sentences:
            for entity in sentence.entities:
                assert entity.get("id") not in self.documentEntitiesById
                self.documentEntitiesById[entity.get("id")] = entity
                      
        for i in range(len(sentences)):
            self.progress.update(1, "Building examples ("+sentences[i].sentence.get("id")+"): ")
            self.processSentence(sentences[i], examples, goldSentences[i] if goldSentences else None)
        
    def buildExamplesFromGraph(self, sentenceGraph, examples, goldGraph=None):
        dg = sentenceGraph.dependencyGraph
        undirected = dg.toUndirected()
        edgeCounts = {x:len(dg.getInEdges(x) + dg.getOutEdges(x)) for x in sentenceGraph.tokens}
        paths = undirected
        
        # Get argument order
        #self.interactionLengths = self.getInteractionEdgeLengths(sentenceGraph, paths)
        
#         # Map tokens to character offsets
#         tokenByOffset = {}
#         for i in range(len(sentenceGraph.tokens)):
#             token = sentenceGraph.tokens[i]
#             if goldGraph != None: # check that the tokenizations match
#                 goldToken = goldGraph.tokens[i]
#                 assert token.get("id") == goldToken.get("id") and token.get("charOffset") == goldToken.get("charOffset")
#             tokenByOffset[token.get("charOffset")] = token.get("id")
        
        # Map gold entities to their head offsets
        goldEntitiesByOffset = {}
        if goldGraph != None:
            for entity in goldGraph.entities:
                offset = entity.get("headOffset")
                assert offset != None
                if not goldEntitiesByOffset.has_key(offset):
                    goldEntitiesByOffset[offset] = []
                goldEntitiesByOffset[offset].append(entity)
        
        if "no_merge" in self.styles:
            mergeInput = False
            entities = sentenceGraph.entities
        else:
            mergeInput = True
            sentenceGraph.mergeInteractionGraph(True)
            entities = sentenceGraph.mergedEntities
            self.exampleStats.addValue("Duplicate entities skipped", len(sentenceGraph.entities) - len(entities))
        
        # Pre-generate features for all tokens in the sentence
        tokens, tokenMap = self.getTokenFeatures(sentenceGraph)
        
        exampleIndex = 0
        for entity in entities: # sentenceGraph.entities:
            if type(entity) in types.StringTypes: # dummy entity for intersentence interactions
                continue
            
            eType = entity.get("type")
            assert eType != None, entity.attrib
            eType = str(eType)
            
            interactions = [x[2] for x in sentenceGraph.getOutInteractions(entity, mergeInput)]
            interactions.sort(key=lambda k: k.get("id"))
            interactionCounts = defaultdict(int)
            validInteractionsByType = defaultdict(list)
            for token in tokens:
                token["interaction"] = None
            for interaction in interactions:
                if interaction.get("event") != "True":
                    continue
                e1 = sentenceGraph.entitiesById[interaction.get("e1")]
                #assert e1 == entity, (e1.attrib, entity.attrib)
                if interaction.get("e2") in sentenceGraph.entitiesById:
                    e2 = sentenceGraph.entitiesById[interaction.get("e2")]
                    if interaction.get("type") in self.structureAnalyzer.getValidEdgeTypes(e1.get("type"), e2.get("type")):
                        validInteractionsByType[interaction.get("type")].append(interaction)
                        e2Token = sentenceGraph.entityHeadTokenByEntity[e2]
                        tokenMap[e2Token]["interaction"] = interaction
                else: # intersentence
                    validInteractionsByType[interaction.get("type")].append(interaction)
                interactionCounts[interaction.get("type")] += 1
            interactionCountString = ",".join([key + "=" + str(interactionCounts[key]) for key in sorted(interactionCounts.keys())])
            #argCombinations = self.getArgumentCombinations(eType, interactions, entity.get("id"))
            intCombinations = []
            validIntTypeCount = 0
            maxArgCount = 0
            if self.debug:
                print >> sys.stderr, entity.get("id"), entity.get("type"), "int:" + interactionCountString, "validInt:" + str(validInteractionsByType)
            for intType in sorted(validInteractionsByType.keys()): # for each argument type the event can have
                validIntTypeCount += 1
                intCombinations.append([])
                minArgs, maxArgs = self.structureAnalyzer.getArgLimits(entity.get("type"), intType)
                if maxArgs > maxArgCount:
                    maxArgCount = maxArgs
                #if maxArgs > 1: # allow any number of arguments for cases like Binding
                #    maxArgs = len(validInteractionsByType[intType])
                for combLen in range(minArgs, maxArgs+1): # for each valid argument count, get all possible combinations. note that there may be zero-lenght combination
                    for singleTypeArgCombination in combinations(validInteractionsByType[intType], combLen):
                        intCombinations[-1].append(singleTypeArgCombination)
                # e.g. theme:[a,b], cause:[d] = [[
            # intCombinations now contains a list of lists, each of which has a tuple for each valid combination
            # of one argument type. Next, we'll make all valid combinations of multiple argument types
            if self.debug:
                print >> sys.stderr, " ", "intCombinations", intCombinations
            argCombinations = combine.combine(*intCombinations)
            if self.debug:
                print >> sys.stderr, " ", "argCombinations", argCombinations
            for i in range(len(argCombinations)):
                argCombinations[i] = sum(argCombinations[i], ())
            #sum(argCombinations, []) # flatten nested list
            if self.debug:
                print >> sys.stderr, " ", "argCombinations flat", argCombinations
            
            for argCombination in argCombinations:
                # Originally binary classification
                if goldGraph != None:
                    isGoldEvent = self.eventIsGold(entity, argCombination, sentenceGraph, goldGraph, goldEntitiesByOffset, goldGraph.interactions)
                    #if eType == "Binding":
                    #    print argCombination[0].get("e1"), len(argCombination), isGoldEvent
                else:
                    isGoldEvent = False
                # Named (multi-)class
                labels = []
                if isGoldEvent:
                    if "binary" in self.styles:
                        labels = ["pos"]
                    else:
                        labels = [entity.get("type")]
                #else:
                #    category = "neg"
                self.exampleStats.beginExample(",".join(labels))
                
                issues = defaultdict(int)
                # early out for proteins etc.
                if validIntTypeCount == 0 and entity.get("given") == "True":
                    self.exampleStats.filter("given-leaf:" + entity.get("type"))
                    if self.debug:
                        print >> sys.stderr, " ", ",".join(labels) +"("+eType+")", "arg combination", argCombination, "LEAF"
                elif self.structureAnalyzer.isValidEntity(entity) or self.structureAnalyzer.isValidEvent(entity, argCombination, self.documentEntitiesById, noUpperLimitBeyondOne = "no_arg_count_upper_limit" in self.styles, issues=issues):
                    if self.debug:
                        print >> sys.stderr, " ", ",".join(labels), "arg combination", argCombination, "VALID"
                    argString = ""
                    for arg in argCombination:
                        argString += "," + arg.get("type") + "=" + arg.get("id")
                    extra = {"xtype":"um","e":entity.get("id"),"i":argString[1:],"etype":eType,"class":",".join(labels)}
                    extra["allInt"] = interactionCountString
                    assert type(extra["etype"]) in types.StringTypes, extra
                    assert type(extra["class"]) in types.StringTypes, ",".join(labels)
                    assert type(extra["i"]) in types.StringTypes, argString
                    features = self.buildFeatures(sentenceGraph, paths, entity, argCombination, interactions, tokens, tokenMap, undirected, edgeCounts)
                    examples.append({"id":sentenceGraph.getSentenceId()+".x"+str(self.exampleIndex), "labels":labels, "features":features, "extra":extra, "doc":sentenceGraph.documentElement.get("id")}) #, "extra":{"eIds":entityIds}}
                    self.exampleIndex += 1
                else: # not a valid event or valid entity
                    if len(issues) == 0: # must be > 0 so that it gets filtered
                        if not self.structureAnalyzer.isValidEntity(entity):
                            issues["INVALID_ENTITY:"+eType] += 1
                        else:
                            issues["UNKNOWN_ISSUE_FOR:"+eType] += 1
                    for key in issues:
                        self.exampleStats.filter(key)
                    if self.debug:
                        print >> sys.stderr, " ", labels, "arg combination", argCombination, "INVALID", issues
                self.exampleStats.endExample()
            
        #return examples
        return exampleIndex
    
    def buildFeatures(self, sentenceGraph, paths, eventEntity, argCombination, allInteractions, tokens, tokenMap, undirected, edgeCounts): #themeEntities, causeEntities=None):
        # NOTE!!!! TODO
        # add also features for arguments present, but not in this combination
        
        argSet = set(argCombination)
        eventToken = tokenMap[sentenceGraph.entityHeadTokenByEntity[eventEntity]]
        eventIndex = eventToken["index"]
        
        exampleLength = int(self.styles.get("el", -1)) if self.exampleLength == None else self.exampleLength
        if self.exampleLength == None:
            self.exampleLength = exampleLength
        outsideLength = int(self.styles.get("ol", 5))
        
        numTokens = len(tokens)
        intTokenIndices = sorted([x["index"] for x in tokens if x.get("interaction") != None])
        eventRange = (eventIndex, eventIndex)
        if len(intTokenIndices) > 0:
            eventRange = (min(eventIndex, intTokenIndices[0]), max(eventIndex, intTokenIndices[-1]))
        relTokens = []
        relMarker = "b"
        for i in range(numTokens):
            if i == eventRange[0]:
                relMarker = "m"
            elif i == eventRange[-1]:
                relMarker = "a"
            
            if i == eventIndex:
                relTokens.append("event")
            elif i in intTokenIndices:
                if tokens[i]["interaction"] in argSet:
                    relTokens.append("arg")
                else:
                    relTokens.append("int")
            else:
                relTokens.append(relMarker)
        
        featureGroups = sorted(self.embeddingInputs.keys())
        wordEmbeddings = [x for x in sorted(self.embeddings.keys()) if self.embeddings[x].wvPath != None]
        features = {x:[] for x in featureGroups}
        for i in range(eventRange[0] - outsideLength, eventRange[1] + outsideLength + 1):
            if i >= 0 and i < numTokens:
                token = tokens[i]
                #tokens.append(token2)
                #if self.debugGold:
                #    self.addFeature("gold", features, ",".join(labels[i]), "[out]")
                interaction = token.get("interaction")
                intType = interaction.get("type") if interaction != None else "[N/A]"
                self.addFeature("int_arg", features, intType if interaction in argSet else "[N/A]", "[out]")
                self.addFeature("int_all", features, intType, "[out]")
                self.addIndex("entities", features, token.get("entities"))
                for wordEmbedding in wordEmbeddings:
                    self.addIndex(wordEmbedding, features, token[wordEmbedding])
                self.addFeature("positions", features, self.getPositionName(i - eventIndex), "[out]")
                self.addFeature("rel_token", features, relTokens[i])
                #self.addIndex("named_entities", features, token["named_entities"])
                self.addIndex("POS", features, token["POS"])
                self.addPathEmbedding(eventToken["element"], token["element"], sentenceGraph.dependencyGraph, undirected, edgeCounts, features)
            else:
                #tokens.append(None)
                for featureGroup in featureGroups:
                    self.addFeature(featureGroup, features, "[pad]")
        return features
    
    def eventIsGold(self, entity, arguments, sentenceGraph, goldGraph, goldEntitiesByOffset, allGoldInteractions):
        offset = entity.get("headOffset")
        if not goldEntitiesByOffset.has_key(offset):
            return False
        eType = entity.get("type")
        goldEntities = goldEntitiesByOffset[offset]
        
        # Check all gold entities for a match
        for goldEntity in goldEntities:
            isGold = True
            
            # The entity type must match
            if goldEntity.get("type") != eType:
                isGold = False
                continue
            goldEntityId = goldEntity.get("id")
            
            # Collect the gold interactions
            goldInteractions = []
            for goldInteraction in allGoldInteractions: #goldGraph.interactions:
                if goldInteraction.get("e1") == goldEntityId and goldInteraction.get("event") == "True":
                    goldInteractions.append(goldInteraction)
            
            # Argument count rules
            if len(goldInteractions) != len(arguments): # total number of edges differs
                isGold = False
                continue
            # count number of edges per type
            argTypeCounts = {}
            for argument in arguments:
                argType = argument.get("type")
                if not argTypeCounts.has_key(argType): argTypeCounts[argType] = 0
                argTypeCounts[argType] += 1
            # count number of gold edges per type
            goldTypeCounts = {}
            for argument in goldInteractions:
                argType = argument.get("type")
                if not goldTypeCounts.has_key(argType): goldTypeCounts[argType] = 0
                goldTypeCounts[argType] += 1
            # argument edge counts per type must match
            if argTypeCounts != goldTypeCounts:
                isGold = False
                continue
            
            # Exact argument matching
            for argument in arguments: # check all edges
                e1 = argument.get("e1")
                e2 = argument.get("e2")
                if e2 not in sentenceGraph.entitiesById: # intersentence argument, assumed to be correct
                    found = True
                    continue
                e2Entity = sentenceGraph.entitiesById[e2]
                e2Offset = e2Entity.get("headOffset")
                e2Type = e2Entity.get("type")
                argType = argument.get("type")
                
                found = False
                for goldInteraction in goldInteractions:
                    if goldInteraction.get("type") == argType:
                        if goldInteraction.get("e2") in goldGraph.entitiesById: # if not, assume this goldInteraction is an intersentence interaction
                            goldE2Entity = goldGraph.entitiesById[goldInteraction.get("e2")] 
                            if goldE2Entity.get("headOffset") == e2Offset and goldE2Entity.get("type") == e2Type:
                                found = True
                                break
                if found == False: # this edge did not have a corresponding gold edge
                    isGold = False
                    break

            # Event is in gold
            if isGold:
                break
        
        return isGold
    
    def defineFeatureGroups(self):
        print >> sys.stderr, "Defining embedding indices"
        self.defineWordEmbeddings()
        self.defineEmbedding("positions")
        self.defineEmbedding("rel_token")
        #self.defineEmbedding("named_entities")
        self.defineEmbedding("entities")
        self.defineEmbedding("int_arg")
        self.defineEmbedding("int_all")
        self.defineEmbedding("POS", vocabularyType="POS")
        ##for i in range(self.pathDepth):
        ##    self.defineEmbedding("path" + str(i), vocabularyType="directed_dependencies")
        #self.defineEmbedding("path", vocabularyType="directed_dependencies", inputNames=["path" + str(i) for i in range(self.pathDepth)])
        for name in ["path" + str(i) for i in range(self.pathDepth)]:
            self.defineEmbedding(name, vocabularyType="directed_dependencies")
        #if self.debugGold:
        #    self.defineEmbedding("gold")