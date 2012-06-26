"""
Edge Examples
"""
__version__ = "$Revision: 1.13 $"

import sys, os
thisPath = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(thisPath,"..")))
sys.path.append(os.path.abspath(os.path.join(thisPath,"../CommonUtils")))
from Core.ExampleBuilder import ExampleBuilder
import Core.ExampleBuilder
from Core.IdSet import IdSet
import Core.ExampleUtils as ExampleUtils
from FeatureBuilders.MultiEdgeFeatureBuilder import MultiEdgeFeatureBuilder
from FeatureBuilders.TriggerFeatureBuilder import TriggerFeatureBuilder
from FeatureBuilders.TokenFeatureBuilder import TokenFeatureBuilder
from FeatureBuilders.BioInferOntologyFeatureBuilder import BioInferOntologyFeatureBuilder
from FeatureBuilders.NodalidaFeatureBuilder import NodalidaFeatureBuilder
#import Graph.networkx_v10rc1 as NX10
from Core.SimpleGraph import Graph
from Utils.ProgressCounter import ProgressCounter
#IF LOCAL
import Utils.BioInfer.OntologyUtils as OntologyUtils
#ENDIF
import combine
import cElementTreeUtils as ETUtils
import gzip
import types

from multiprocessing import Process

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
    def __init__(self, style="trigger_features:typed:directed:no_linear:entities:genia_limits:noMasking:maxFeatures", length=None, types=[], featureSet=None, classSet=None):
        # reset style regardless of input
        style="trigger_features:typed:directed:no_linear:entities:genia_limits:noMasking:maxFeatures"
        if featureSet == None:
            featureSet = IdSet()
        if classSet == None:
            classSet = IdSet(1)
        else:
            classSet = classSet
        assert( classSet.getId("neg") == 1 )
        
        ExampleBuilder.__init__(self, classSet=classSet, featureSet=featureSet)
        
        self.styles = self.getParameters(style, ["trigger_features","typed","directed","no_linear","entities","genia_limits",
            "noAnnType", "noMasking", "maxFeatures", "no_merge", "disable_entity_features", 
            "disable_single_element_features", "disable_ngram_features", "disable_path_edge_features"])
        self.multiEdgeFeatureBuilder = MultiEdgeFeatureBuilder(self.featureSet)
        self.multiEdgeFeatureBuilder.noAnnType = self.styles["noAnnType"]
        self.multiEdgeFeatureBuilder.maskNamedEntities = not self.styles["noMasking"]
        self.multiEdgeFeatureBuilder.maximum = self.styles["maxFeatures"]
        self.tokenFeatureBuilder = TokenFeatureBuilder(self.featureSet)
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
        for interaction in sentenceGraph.interactions:
            # Calculated interaction edge dep and lin length
            e1 = sentenceGraph.entitiesById[interaction.get("e1")]
            e2 = sentenceGraph.entitiesById[interaction.get("e2")]
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
        return interactionLengths
    
    def eventIsGold(self, entity, arguments, sentenceGraph, goldGraph, goldEntitiesByOffset):
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
            for goldInteraction in goldGraph.interactions:
                if goldInteraction.get("e1") == goldEntityId:
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
                e2Entity = sentenceGraph.entitiesById[e2]
                e2Offset = e2Entity.get("headOffset")
                e2Type = e2Entity.get("type")
                argType = argument.get("type")
                
                found = False
                for goldInteraction in goldInteractions:
                    if goldInteraction.get("type") == argType:
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
    
    def getArgumentCombinations(self, eType, interactions, entityId=None):
        combs = []
        if eType == "Binding":
            # Making examples for only all-together/all-separate cases
            # doesn't work, since even gold data has several cases of
            # overlapping bindings with different numbers of arguments
            #if len(interactions) > 0:
            #    return [interactions]
            #else:
            #    return interactions
            
            # Skip causes
            themes = []
            for interaction in interactions:
                if interaction.get("type") == "Theme":
                    themes.append(interaction)
                
            for i in range(len(themes)):
                # Looking at a2-normalize.pl reveals that there can be max 6 themes
                # Based on training+devel data, four is maximum
                if i < 10: #4: 
                    for j in combinations(themes, i+1):
                        combs.append(j)
#                if len(combs) >= 100:
#                    print >> sys.stderr, "Warning, truncating unmerging examples at 100 for Binding entity", entityId
#                    break
            return combs
        elif eType == "Process": # For ID-task
            argCombinations = []
            argCombinations.append([]) # process can have 0 interactions
            for interaction in interactions:
                if interaction.get("type") == "Participant":
                    argCombinations.append([interaction])
            return argCombinations
        else: # one of the regulation-types, or one of the simple types
            themes = []
            causes = []
            siteArgs = []
            contextGenes = []
            sideChains = []
            locTargets = []
            for interaction in interactions:
                iType = interaction.get("type")
                #assert iType in ["Theme", "Cause"], (iType, ETUtils.toStr(interaction))
                if iType not in ["Theme", "Cause", "SiteArg", "Contextgene", "Sidechain"]: # "AtLoc", "ToLoc"]:
                    continue
                if iType == "Theme":
                    themes.append(interaction)
                elif iType == "Cause":
                    causes.append(interaction)
                elif iType == "SiteArg":
                    siteArgs.append(interaction)
                elif iType == "Contextgene":
                    contextGenes.append(interaction)
                elif iType == "Sidechain":
                    sideChains.append(interaction)
                elif iType in ["AtLoc", "ToLoc"]:
                    locTargets.append(iType)
                else:
                    assert False, (iType, interaction.get("id"))
            # Limit arguments to event types that can have them
            if eType.find("egulation") == -1 and eType != "Catalysis": 
                causes = []
            if eType != "Glycosylation": sideChains = []
            if eType not in ["Acetylation", "Methylation"]: contextGenes = []
            if eType == "Catalysis": siteArgs = []
            # Themes can always appear alone
            themeAloneCombinations = []
            for theme in themes:
                themeAloneCombinations.append([theme])
            #print "Combine", combine.combine(themes, causes), "TA", themeAloneCombinations
            return combine.combine(themes, causes) \
                   + combine.combine(themes, siteArgs) \
                   + combine.combine(themes, sideChains) \
                   + combine.combine(themes, contextGenes) \
                   + combine.combine(themes, siteArgs, sideChains) \
                   + combine.combine(themes, siteArgs, contextGenes) \
                   + combine.combine(themes, locTargets) \
                   + themeAloneCombinations
            
    def buildExamplesFromGraph(self, sentenceGraph, outfile, goldGraph=None):
        """
        Build examples for a single sentence. Returns a list of examples.
        See Core/ExampleUtils for example format.
        """
        self.multiEdgeFeatureBuilder.setFeatureVector(resetCache=True)
        self.triggerFeatureBuilder.initSentence(sentenceGraph)
        
        #examples = []
        exampleIndex = 0
        
        #undirected = self.nxMultiDiGraphToUndirected(sentenceGraph.dependencyGraph)
        #paths = NX10.all_pairs_shortest_path(undirected, cutoff=999)
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
        
        # Generate examples based on interactions between entities or interactions between tokens
#        interactionsByEntityId = {}
#        for entity in sentenceGraph.entities:
#            interactionsByEntityId[entity.get("id")] = []
#        for interaction in sentenceGraph.interactions:
#            if interaction.get("type") == "neg":
#                continue
#            e1Id = interaction.get("e1")
#            interactionsByEntityId[e1Id].append(interaction)
        if self.styles["no_merge"]:
            mergeInput = False
            entities = sentenceGraph.entities
        else:
            mergeInput = True
            sentenceGraph.mergeInteractionGraph(True)
            entities = sentenceGraph.mergedEntities
        
        exampleIndex = 0
        for entity in entities: # sentenceGraph.entities:
            eType = entity.get("type")
            assert eType != None, entity.attrib
            eType = str(eType)
            #if eType not in ["Binding", "Positive_regulation", "Negative_regulation", "Regulation"]:
            #    continue
            
            #if not goldEntitiesByOffset.has_key(entity.get("headOffset")):
            #    continue
            
            #interactions = interactionsByEntityId[entity.get("id")]
            interactions = [x[2] for x in sentenceGraph.getOutInteractions(entity, mergeInput)]
            argCombinations = self.getArgumentCombinations(eType, interactions, entity.get("id"))
            #if len(argCombinations) <= 1:
            #    continue
            assert argCombinations != None, (entity.get("id"), entity.get("type"))
            for argCombination in argCombinations:
                if eType != "Process":
                    assert len(argCombination) > 0, eType + ": " + str(argCombinations)
                # Originally binary classification
                if goldGraph != None:
                    isGoldEvent = self.eventIsGold(entity, argCombination, sentenceGraph, goldGraph, goldEntitiesByOffset)
                    #if eType == "Binding":
                    #    print argCombination[0].get("e1"), len(argCombination), isGoldEvent
                else:
                    isGoldEvent = False
                # Named (multi-)class
                if isGoldEvent:
                    #category = "event"
                    category = eType
                    if category.find("egulation") != -1:
                        category = "All_regulation"
                    elif category != "Binding":
                        category = "Other" #"simple6"
                else:
                    category = "neg"
                    
                features = {}
                
                argString = ""
                for arg in argCombination:
                    argString += "," + arg.get("id")
                extra = {"xtype":"um","e":entity.get("id"),"i":argString[1:],"etype":eType,"class":category}
                assert type(extra["etype"]) == types.StringType, extra
                self.exampleStats.addExample(category)
                example = self.buildExample(sentenceGraph, paths, entity, argCombination, interactions)
                example[0] = sentenceGraph.getSentenceId()+".x"+str(exampleIndex)
                example[1] = self.classSet.getId(category)
                example[3] = extra
                #examples.append( example )
                ExampleUtils.appendExamples([example], outfile)
                exampleIndex += 1
            
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
        
        #argThemeCount = 0
        #argCauseCount = 0
        argCounts = {}
        # Current example's edge combination
        for arg in argCombination:
            argType = arg.get("type")
            if argType not in argCounts: 
                argCounts[argType] = 0
            argCounts[argType] += 1
            tag = "arg" + argType
            if eventEntityType == "Binding" and argType == "Theme":
                tag += str(interactionIndex[arg])
            self.buildArgumentFeatures(sentenceGraph, paths, features, eventToken, arg, tag)
##            if arg.get("type") == "Theme":
##                #argThemeCount += 1
##                tag = "argTheme"
##                self.buildArgumentFeatures(sentenceGraph, paths, features, eventToken, arg, tag)
#            #elif arg.get("type") == "Cause": # Cause
#            #    #argCauseCount += 1
#            #    self.buildArgumentFeatures(sentenceGraph, paths, features, eventToken, arg, "argCause")
#            else:               
#                self.buildArgumentFeatures(sentenceGraph, paths, features, eventToken, arg, "arg"+argType)         
        
        # Edge group context
        #contextThemeCount = 0
        #contextCauseCount = 0
        contextCounts = {}
        for interaction in allInteractions:
            if interaction in argCombination: # Already part of current example's combination
                continue
            contextArgType = interaction.get("type")
            if contextArgType not in contextCounts: 
                contextCounts[contextArgType] = 0
            contextCounts[contextArgType] += 1
            tag = "conArg" + contextArgType
            if eventEntityType == "Binding" and contextArgType == "Theme":
                tag += str(interactionIndex[interaction])
            self.buildArgumentFeatures(sentenceGraph, paths, features, eventToken, interaction, tag)
#            if interaction.get("type") == "Theme":
#                contextThemeCount += 1
#                tag = "conTheme"
#                self.buildArgumentFeatures(sentenceGraph, paths, features, eventToken, interaction, tag)
#                if eventEntityType == "Binding":
#                    tag += str(interactionIndex[interaction])
#                    self.buildArgumentFeatures(sentenceGraph, paths, features, eventToken, interaction, tag)
#            else: # Cause
#                contextCauseCount += 1
#                self.buildArgumentFeatures(sentenceGraph, paths, features, eventToken, interaction, "conCause")
        
        self.setFeature("argCount", len(argCombination))
        self.setFeature("argCount_" + str(len(argCombination)), 1)
        self.setFeature("interactionCount", len(allInteractions))
        self.setFeature("interactionCount_" + str(len(allInteractions)), 1)
        
        #self.setFeature("argThemeCount", argThemeCount)
        #self.setFeature("argThemeCount_" + str(argThemeCount), 1)
        #self.setFeature("argCauseCount", argCauseCount)
        #self.setFeature("argCauseCount_" + str(argCauseCount), 1)
        for key in sorted(argCounts.keys()):
            self.setFeature("arg" + key + "Count", argCounts[key])
            self.setFeature("arg" + key + "Count_" + str(argCounts[key]), 1)
            
        #self.setFeature("interactionThemeCount", contextThemeCount)
        #self.setFeature("interactionThemeCount_" + str(contextThemeCount), 1)
        #self.setFeature("interactionCauseCount", contextCauseCount)
        #self.setFeature("interactionCauseCount_" + str(contextCauseCount), 1)
        for key in sorted(contextCounts.keys()):
            self.setFeature("contextArg" + key + "Count", contextCounts[key])
            self.setFeature("contextArg" + key + "Count_" + str(contextCounts[key]), 1)      
        
        self.triggerFeatureBuilder.tag = ""
        self.triggerFeatureBuilder.setFeatureVector(None)
        
        # Common features
#        if e1Type.find("egulation") != -1: # leave r out to avoid problems with capitalization
#            if entity2.get("isName") == "True":
#                features[self.featureSet.getId("GENIA_regulation_of_protein")] = 1
#            else:
#                features[self.featureSet.getId("GENIA_regulation_of_event")] = 1

        # define extra attributes
        return [None,None,features,None]

    def buildArgumentFeatures(self, sentenceGraph, paths, features, eventToken, arg, tag):
        argEntity = sentenceGraph.entitiesById[arg.get("e2")]
        argToken = sentenceGraph.entityHeadTokenByEntity[argEntity]
        self.buildEdgeFeatures(sentenceGraph, paths, features, eventToken, argToken, tag)
        self.triggerFeatureBuilder.tag = tag + "trg_"
        self.triggerFeatureBuilder.buildFeatures(argToken)
        if argEntity.get("isName") == "True":
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
            argEntity = sentenceGraph.entitiesById[arg.get("e2")]
            argToken = sentenceGraph.entityHeadTokenByEntity[argEntity]
            argTokenIndices.add(indexByToken[argToken])
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
            
