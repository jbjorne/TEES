"""
Edge Examples
"""
__version__ = "$Revision: 1.13 $"

import sys, os
thisPath = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(thisPath,"..")))
from ExampleBuilders.ExampleBuilder import ExampleBuilder
from Core.IdSet import IdSet
import Core.ExampleUtils as ExampleUtils
from FeatureBuilders.MultiEdgeFeatureBuilder import MultiEdgeFeatureBuilder
from FeatureBuilders.TriggerFeatureBuilder import TriggerFeatureBuilder
#from FeatureBuilders.TokenFeatureBuilder import TokenFeatureBuilder
from Core.SimpleGraph import Graph
from Utils.ProgressCounter import ProgressCounter
import Utils.Libraries.combine as combine
import Utils.ElementTreeUtils as ETUtils
import gzip
import types
from collections import defaultdict

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

class UnmergingExampleBuilder(ExampleBuilder):
    """
    This example builder makes unmerging examples, i.e. examples describing
    potential events.
    """
    #def __init__(self, style="trigger_features:typed:directed:no_linear:entities:genia_limits:noMasking:maxFeatures", length=None, types=[], featureSet=None, classSet=None):
    def __init__(self, style=None, length=None, types=[], featureSet=None, classSet=None):
        # reset style regardless of input
        #style="trigger_features:typed:directed:no_linear:entities:genia_limits:noMasking:maxFeatures"
        if featureSet == None:
            featureSet = IdSet()
        if classSet == None:
            classSet = IdSet(1)
        else:
            classSet = classSet
        assert( classSet.getId("neg") == 1 )
        
        ExampleBuilder.__init__(self, classSet=classSet, featureSet=featureSet)
        
        defaultNone = ["binary", "trigger_features","typed","directed","no_linear","entities","genia_limits",
            "noAnnType", "noMasking", "maxFeatures", "no_merge", "disable_entity_features", 
            "disable_single_element_features", "disable_ngram_features", "disable_path_edge_features"]
        defaultParameters = {}
        for name in defaultNone:
            defaultParameters[name] = None
        defaultParameters["keep_intersentence"] = False
        defaultParameters["keep_intersentence_gold"] = True
        defaultParameters["no_arg_count_upper_limit"] = False
        self.styles = self._setDefaultParameters(defaultParameters)
        self.styles = self.getParameters(style)
        self.multiEdgeFeatureBuilder = MultiEdgeFeatureBuilder(self.featureSet)
        self.multiEdgeFeatureBuilder.noAnnType = self.styles["noAnnType"]
        self.multiEdgeFeatureBuilder.maskNamedEntities = not self.styles["noMasking"]
        self.multiEdgeFeatureBuilder.maximum = self.styles["maxFeatures"]
        #self.tokenFeatureBuilder = TokenFeatureBuilder(self.featureSet)
        self.pathLengths = length
        assert(self.pathLengths == None)
        self.types = types

        self.triggerFeatureBuilder = TriggerFeatureBuilder(self.featureSet)
        self.triggerFeatureBuilder.useNonNameEntities = True
        
        #self.outFile = open("exampleTempFile.txt","wt")
    
    def getInteractionEdgeLengths(self, sentenceGraph, paths):
        """
        Return dependency and linear length of all interaction edges
        (measured between the two tokens).
        """
        interactionLengths = {}
        count = 0
        for interaction in sentenceGraph.interactions:
            # Calculated interaction edge dep and lin length
            e1Id = interaction.get("e1")
            e2Id = interaction.get("e2")
            if e2Id not in sentenceGraph.entitiesById: # intersentence interaction
                interactionLengths[interaction] = (interaction, -count, -count, -count)
                continue
            e1 = sentenceGraph.entitiesById[e1Id]
            e2 = sentenceGraph.entitiesById[e2Id]
            t1 = sentenceGraph.entityHeadTokenByEntity[e1]
            t2 = sentenceGraph.entityHeadTokenByEntity[e2]
            # Get dep path length
            if t1 != t2:
                path = paths.getPaths(t1, t2)
            if t1 != t2 and len(path) > 0:
                pathLength = min(len(x) for x in path) #len(paths[t1][t2])
            else: # no dependencyPath
                pathLength = 999999 # more than any real path
            # Linear distance
            t1Pos = -1
            t2Pos = -1
            for i in range(len(sentenceGraph.tokens)):
                if sentenceGraph.tokens[i] == t1:
                    t1Pos = i
                    if t2Pos != -1:
                        break
                if sentenceGraph.tokens[i] == t2:
                    t2Pos = i
                    if t1Pos != -1:
                        break
            linLength = abs(t1Pos - t2Pos)
            interactionLengths[interaction] = (interaction, pathLength, linLength, t2Pos)
            count += 1
        return interactionLengths
    
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
    
    def sortInteractionsById(self, interactions):
        # The order of the interactions affects the order of the unmerging examples, and this 
        # affects performance. It's not clear whether this is what really happens, or whether
        # the order of the interactions has some effect on the consistency of the unmerging
        # features (it shouldn't). However, in case it does, this function is left here for now,
        # although it shouldn't be needed at all. In any case the impact is minimal, for GE
        # 53.22 vs 53.28 on the development set.
        pairs = []
        for interaction in interactions:
            pairs.append( (int(interaction.get("id").split(".i")[-1]), interaction) )
        pairs.sort()
        return [x[1] for x in pairs]
    
    def processDocument(self, sentences, goldSentences, outfile, structureAnalyzer=None):
        self.documentEntitiesById = {}
        for sentence in sentences:
            for entity in sentence.entities:
                assert entity.get("id") not in self.documentEntitiesById
                self.documentEntitiesById[entity.get("id")] = entity
                      
        for i in range(len(sentences)):
            sentence = sentences[i]
            goldSentence = None
            if goldSentences != None:
                goldSentence = goldSentences[i]
            self.progress.update(1, "Building examples ("+sentence.sentence.get("id")+"): ")
            self.processSentence(sentence, outfile, goldSentence, structureAnalyzer=structureAnalyzer)
    
    def buildExamplesFromGraph(self, sentenceGraph, outfile, goldGraph=None, structureAnalyzer=None):
        """
        Build examples for a single sentence. Returns a list of examples.
        See Core/ExampleUtils for example format.
        """
        self.multiEdgeFeatureBuilder.setFeatureVector(resetCache=True)
        self.triggerFeatureBuilder.initSentence(sentenceGraph)        
        
        exampleIndex = 0
        undirected = sentenceGraph.dependencyGraph.toUndirected()
        paths = undirected
        
        # Get argument order
        self.interactionLenghts = self.getInteractionEdgeLengths(sentenceGraph, paths)
        
        # Map tokens to character offsets
        tokenByOffset = {}
        for i in range(len(sentenceGraph.tokens)):
            token = sentenceGraph.tokens[i]
            if goldGraph != None: # check that the tokenizations match
                goldToken = goldGraph.tokens[i]
                assert token.get("id") == goldToken.get("id") and token.get("charOffset") == goldToken.get("charOffset")
            tokenByOffset[token.get("charOffset")] = token.get("id")
        
        # Map gold entities to their head offsets
        goldEntitiesByOffset = {}
        if goldGraph != None:
            for entity in goldGraph.entities:
                offset = entity.get("headOffset")
                assert offset != None
                if not goldEntitiesByOffset.has_key(offset):
                    goldEntitiesByOffset[offset] = []
                goldEntitiesByOffset[offset].append(entity)
        
        if self.styles["no_merge"]:
            mergeInput = False
            entities = sentenceGraph.entities
        else:
            mergeInput = True
            sentenceGraph.mergeInteractionGraph(True)
            entities = sentenceGraph.mergedEntities
            self.exampleStats.addValue("Duplicate entities skipped", len(sentenceGraph.entities) - len(entities))
        
        exampleIndex = 0
        for entity in entities: # sentenceGraph.entities:
            if type(entity) in types.StringTypes: # dummy entity for intersentence interactions
                continue
            
            eType = entity.get("type")
            assert eType != None, entity.attrib
            eType = str(eType)
            
            interactions = [x[2] for x in sentenceGraph.getOutInteractions(entity, mergeInput)]
            interactions = self.sortInteractionsById(interactions)
            interactionCounts = defaultdict(int)
            validInteractionsByType = defaultdict(list)
            for interaction in interactions:
                if interaction.get("event") != "True":
                    continue
                e1 = sentenceGraph.entitiesById[interaction.get("e1")]
                if interaction.get("e2") in sentenceGraph.entitiesById:
                    e2 = sentenceGraph.entitiesById[interaction.get("e2")]
                    if interaction.get("type") in structureAnalyzer.getValidEdgeTypes(e1.get("type"), e2.get("type")):
                        validInteractionsByType[interaction.get("type")].append(interaction)
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
                minArgs, maxArgs = structureAnalyzer.getArgLimits(entity.get("type"), intType)
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
                if isGoldEvent:
#                    category = "zeroArg"
#                    if validIntTypeCount == 1:
#                        category = "singleArg" # event has 0-1 arguments (old simple6)
#                    if validIntTypeCount > 1:
#                        category = "multiType" # event has arguments of several types, 0-1 of each (old Regulation)
#                    if maxArgCount > 1:
#                        category = "multiArg" # event can have 2-n of at least one argument type (old Binding)
                    if self.styles["binary"]:
                        category = "pos"
                    else:
                        category = entity.get("type")
                        
                    assert category != None
                else:
                    category = "neg"
                self.exampleStats.beginExample(category)
                
                issues = defaultdict(int)
                # early out for proteins etc.
                if validIntTypeCount == 0 and entity.get("given") == "True":
                    self.exampleStats.filter("given-leaf:" + entity.get("type"))
                    if self.debug:
                        print >> sys.stderr, " ", category +"("+eType+")", "arg combination", argCombination, "LEAF"
                elif structureAnalyzer.isValidEntity(entity) or structureAnalyzer.isValidEvent(entity, argCombination, self.documentEntitiesById, noUpperLimitBeyondOne=self.styles["no_arg_count_upper_limit"], issues=issues):
                    if self.debug:
                        print >> sys.stderr, " ", category, "arg combination", argCombination, "VALID"
                    argString = ""
                    for arg in argCombination:
                        argString += "," + arg.get("type") + "=" + arg.get("id")
                    extra = {"xtype":"um","e":entity.get("id"),"i":argString[1:],"etype":eType,"class":category}
                    extra["allInt"] = interactionCountString
                    assert type(extra["etype"]) in types.StringTypes, extra
                    assert type(extra["class"]) in types.StringTypes, category
                    assert type(extra["i"]) in types.StringTypes, argString
                    example = self.buildExample(sentenceGraph, paths, entity, argCombination, interactions)
                    example[0] = sentenceGraph.getSentenceId()+".x"+str(exampleIndex)
                    example[1] = self.classSet.getId(category)
                    example[3] = extra
                    #examples.append( example )
                    ExampleUtils.appendExamples([example], outfile)
                    exampleIndex += 1
                else: # not a valid event or valid entity
                    if len(issues) == 0: # must be > 0 so that it gets filtered
                        if not structureAnalyzer.isValidEntity(entity):
                            issues["INVALID_ENTITY:"+eType] += 1
                        else:
                            issues["UNKNOWN_ISSUE_FOR:"+eType] += 1
                    for key in issues:
                        self.exampleStats.filter(key)
                    if self.debug:
                        print >> sys.stderr, " ", category, "arg combination", argCombination, "INVALID", issues
                self.exampleStats.endExample()
            
        #return examples
        return exampleIndex
    
    def buildExample(self, sentenceGraph, paths, eventEntity, argCombination, allInteractions): #themeEntities, causeEntities=None):
        # NOTE!!!! TODO
        # add also features for arguments present, but not in this combination
        
        features = {}
        self.features = features
        
        self.buildInterArgumentBagOfWords(argCombination, sentenceGraph)
        
        eventEntityType = eventEntity.get("type")
        if eventEntityType == "Binding":
            interactionIndex = {}
            groupInteractionLengths = []
            for interaction in allInteractions:
                groupInteractionLengths.append(self.interactionLenghts[interaction])
            groupInteractionLengths.sort(compareInteractionPrecedence)
            #print groupInteractionLengths
            for i in range(len(groupInteractionLengths)):
                interactionIndex[groupInteractionLengths[i][0]] = i
        
        eventToken = sentenceGraph.entityHeadTokenByEntity[eventEntity]
        self.triggerFeatureBuilder.setFeatureVector(self.features)
        self.triggerFeatureBuilder.tag = "trg_"
        self.triggerFeatureBuilder.buildFeatures(eventToken)
        self.triggerFeatureBuilder.tag = None
        
        #self.setFeature("rootType_"+eventEntity.get("type"), 1)
        
        argThemeCount = 0
        argCauseCount = 0
        argCounts = {}
        # Current example's edge combination
        for arg in argCombination:
            if arg.get("type") == "Theme":
                argThemeCount += 1
                tag = "argTheme"
                self.buildArgumentFeatures(sentenceGraph, paths, features, eventToken, arg, tag)
                if eventEntityType == "Binding":
                    tag += str(interactionIndex[arg])
                    self.buildArgumentFeatures(sentenceGraph, paths, features, eventToken, arg, tag)
            elif arg.get("type") == "Cause": # Cause
                argCauseCount += 1
                self.buildArgumentFeatures(sentenceGraph, paths, features, eventToken, arg, "argCause")
            else:
                argType = arg.get("type")
                if argType not in argCounts: argCounts[argType] = 0
                self.buildArgumentFeatures(sentenceGraph, paths, features, eventToken, arg, "arg"+argType)
                argCounts[argType] += 1
        
        # Edge group context
        contextThemeCount = 0
        contextCauseCount = 0
        for interaction in allInteractions:
            if interaction in argCombination: # Already part of current example's combination
                continue
            if interaction.get("type") == "Theme":
                contextThemeCount += 1
                tag = "conTheme"
                self.buildArgumentFeatures(sentenceGraph, paths, features, eventToken, interaction, tag)
                if eventEntityType == "Binding":
                    tag += str(interactionIndex[interaction])
                    self.buildArgumentFeatures(sentenceGraph, paths, features, eventToken, interaction, tag)
            else: # Cause
                contextCauseCount += 1
                self.buildArgumentFeatures(sentenceGraph, paths, features, eventToken, interaction, "conCause")
        
        self.setFeature("argCount", len(argCombination))
        self.setFeature("argCount_" + str(len(argCombination)), 1)
        self.setFeature("interactionCount", len(allInteractions))
        self.setFeature("interactionCount_" + str(len(allInteractions)), 1)
        
        self.setFeature("argThemeCount", argThemeCount)
        self.setFeature("argThemeCount_" + str(argThemeCount), 1)
        self.setFeature("argCauseCount", argCauseCount)
        self.setFeature("argCauseCount_" + str(argCauseCount), 1)
        for key in sorted(argCounts.keys()):
            self.setFeature("arg" + key + "Count", argCounts[key])
            self.setFeature("arg" + key + "Count_" + str(argCounts[key]), 1)
            
        self.setFeature("interactionThemeCount", contextThemeCount)
        self.setFeature("interactionThemeCount_" + str(contextThemeCount), 1)
        self.setFeature("interactionCauseCount", contextCauseCount)
        self.setFeature("interactionCauseCount_" + str(contextCauseCount), 1)        
        
        self.triggerFeatureBuilder.tag = ""
        self.triggerFeatureBuilder.setFeatureVector(None)
    
        # Common features
#        if e1Type.find("egulation") != -1: # leave r out to avoid problems with capitalization
#            if entity2.get("given") == "True":
#                features[self.featureSet.getId("GENIA_regulation_of_protein")] = 1
#            else:
#                features[self.featureSet.getId("GENIA_regulation_of_event")] = 1

        # define extra attributes
        return [None,None,features,None]

    def buildArgumentFeatures(self, sentenceGraph, paths, features, eventToken, arg, tag):
        if arg.get("e2") not in sentenceGraph.entitiesById: # intersentence argument
            return
        argEntity = sentenceGraph.entitiesById[arg.get("e2")]
        argToken = sentenceGraph.entityHeadTokenByEntity[argEntity]
        self.buildEdgeFeatures(sentenceGraph, paths, features, eventToken, argToken, tag)
        self.triggerFeatureBuilder.tag = tag + "trg_"
        self.triggerFeatureBuilder.buildFeatures(argToken)
        if argEntity.get("given") == "True":
            self.setFeature(tag+"Protein", 1)
        else:
            self.setFeature(tag+"Event", 1)
            self.setFeature("nestingEvent", 1)
        self.setFeature(tag+"_"+argEntity.get("type"), 1)
    
    def buildEdgeFeatures(self, sentenceGraph, paths, features, eventToken, argToken, tag):
        #eventToken = sentenceGraph.entityHeadTokenByEntity[eventNode]
        #argToken = sentenceGraph.entityHeadTokenByEntity[argNode]
        self.multiEdgeFeatureBuilder.tag = tag + "_"
        self.multiEdgeFeatureBuilder.setFeatureVector(features, None, None, False)
        
        self.setFeature(tag+"_present", 1)
        
        path = paths.getPaths(eventToken, argToken)
        if eventToken != argToken and len(path) > 0:
            path = path[0]
        else:
            path = [eventToken, argToken]
            #edges = None
        
        if not self.styles["disable_entity_features"]:
            self.multiEdgeFeatureBuilder.buildEntityFeatures(sentenceGraph)
        self.multiEdgeFeatureBuilder.buildPathLengthFeatures(path)
        #if not "disable_terminus_features" in self.styles:
        #    self.multiEdgeFeatureBuilder.buildTerminusTokenFeatures(path, sentenceGraph) # remove for fast
        if not self.styles["disable_single_element_features"]:
            self.multiEdgeFeatureBuilder.buildSingleElementFeatures(path, sentenceGraph)
        if not self.styles["disable_ngram_features"]:
            self.multiEdgeFeatureBuilder.buildPathGrams(2, path, sentenceGraph) # remove for fast
            self.multiEdgeFeatureBuilder.buildPathGrams(3, path, sentenceGraph) # remove for fast
            self.multiEdgeFeatureBuilder.buildPathGrams(4, path, sentenceGraph) # remove for fast
        if not self.styles["disable_path_edge_features"]:
            self.multiEdgeFeatureBuilder.buildPathEdgeFeatures(path, sentenceGraph)
        #self.multiEdgeFeatureBuilder.buildSentenceFeatures(sentenceGraph)
        self.multiEdgeFeatureBuilder.setFeatureVector(None, None, None, False)
        self.multiEdgeFeatureBuilder.tag = ""
    
    def buildInterArgumentBagOfWords(self, arguments, sentenceGraph):
        if len(arguments) < 2:
            return

        indexByToken = {}
        for i in range(len(sentenceGraph.tokens)):
            indexByToken[sentenceGraph.tokens[i]] = i
        
        argTokenIndices = set()
        for arg in arguments:
            if arg.get("e2") in sentenceGraph.entitiesById: # skip intersentence interactions
                argEntity = sentenceGraph.entitiesById[arg.get("e2")]
                argToken = sentenceGraph.entityHeadTokenByEntity[argEntity]
                argTokenIndices.add(indexByToken[argToken])
        if len(argTokenIndices) < 1:
            return
        minIndex = min(argTokenIndices)
        maxIndex = max(argTokenIndices)
        self.setFeature("argBoWRange", (maxIndex-minIndex))
        self.setFeature("argBoWRange_" + str(maxIndex-minIndex), 1)
        bow = set()
        for i in range(minIndex+1, maxIndex):
            token = sentenceGraph.tokens[i]
            if len(sentenceGraph.tokenIsEntityHead[token]) == 0 and not sentenceGraph.tokenIsName[token]:
                bow.add(token.get("text"))
        bow = sorted(list(bow))
        for word in bow:
            self.setFeature("argBoW_"+word, 1)
            if word in ["/", "-"]:
                self.setFeature("argBoW_slashOrHyphen", 1)
        if len(bow) == 1:
            self.setFeature("argBoWonly_"+bow[0], 1)
            if bow[0] in ["/", "-"]:
                self.setFeature("argBoWonly_slashOrHyphen", 1)
            
