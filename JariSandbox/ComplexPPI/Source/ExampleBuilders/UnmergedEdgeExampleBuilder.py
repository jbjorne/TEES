"""
Edge Examples
"""
__version__ = "$Revision: 1.3 $"

import sys, os
import types
thisPath = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(thisPath,"..")))
from Core.ExampleBuilder import ExampleBuilder
import Core.ExampleBuilder
from Core.IdSet import IdSet
import Core.ExampleUtils as ExampleUtils
from FeatureBuilders.MultiEdgeFeatureBuilder import MultiEdgeFeatureBuilder
from FeatureBuilders.TokenFeatureBuilder import TokenFeatureBuilder
from FeatureBuilders.BioInferOntologyFeatureBuilder import BioInferOntologyFeatureBuilder
from FeatureBuilders.NodalidaFeatureBuilder import NodalidaFeatureBuilder
import Graph.networkx_v10rc1 as NX10
#IF LOCAL
import Utils.BioInfer.OntologyUtils as OntologyUtils
#ENDIF

def compareEntityPrecedence(e1, e2):
    """
    e1/e2 = (#arg, sum(arg dep length), sum(arg lin length))
    """
    if e1[0] > e2[0]:
        return 1
    elif e1[0] < e2[0]:
        return -1
    else: # same number of arguments
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
                assert False, ("Precedence error",e1,e2)

class UnmergedEdgeExampleBuilder(ExampleBuilder):
    def __init__(self, style=["typed","directed","headsOnly"], length=None, types=[], featureSet=None, classSet=None):
        if featureSet == None:
            featureSet = IdSet()
        if classSet == None:
            classSet = IdSet(1)
        else:
            classSet = classSet
        assert( classSet.getId("neg") == 1 )
        
        ExampleBuilder.__init__(self, classSet=classSet, featureSet=featureSet)
        self.styles = style
        
        self.multiEdgeFeatureBuilder = MultiEdgeFeatureBuilder(self.featureSet)
        if "noAnnType" in self.styles:
            self.multiEdgeFeatureBuilder.noAnnType = True
        if "noMasking" in self.styles:
            self.multiEdgeFeatureBuilder.maskNamedEntities = False
        if "maxFeatures" in self.styles:
            self.multiEdgeFeatureBuilder.maximum = True
        self.tokenFeatureBuilder = TokenFeatureBuilder(self.featureSet)
        self.pathLengths = length
        assert(self.pathLengths == None)
        self.types = types
        if "random" in self.styles:
            from FeatureBuilders.RandomFeatureBuilder import RandomFeatureBuilder
            self.randomFeatureBuilder = RandomFeatureBuilder(self.featureSet)
        
        #self.outFile = open("exampleTempFile.txt","wt")

    @classmethod
    def run(cls, input, output, parse, tokenization, style, idFileTag=None):
        classSet, featureSet = cls.getIdSets(idFileTag)
        if style == None:
            e = UnmergedEdgeExampleBuilder(classSet=classSet, featureSet=featureSet)
        else:
            e = UnmergedEdgeExampleBuilder(style=style, classSet=classSet, featureSet=featureSet)
        sentences = cls.getSentences(input, parse, tokenization)
        e.buildExamplesForSentences(sentences, output, idFileTag)
        print e.classSet.Ids
    
    def definePredictedValueRange(self, sentences, elementName):
        self.multiEdgeFeatureBuilder.definePredictedValueRange(sentences, elementName)                        
    
    def getPredictedValueRange(self):
        return self.multiEdgeFeatureBuilder.predictedRange
    
    def filterEdgesByType(self, edges, typesToInclude):
        if len(typesToInclude) == 0:
            return edges
        edgesToKeep = []
        for edge in edges:
            if edge.get("type") in typesToInclude:
                edgesToKeep.append(edge)
        return edgesToKeep
        
    def getCategoryName(self, sentenceGraph, e1, e2, directed=True):
        # Dummies are potential entities that do not exist in the 
        # training data. If both entities of an interaction are dummies
        # it can't exist in the training data and is therefore a negative
        if e1[2] or e2[2]:
            return "neg"
        
        e1 = e1[0]
        e2 = e2[0]
        
        interactions = sentenceGraph.getInteractions(e1, e2)
        if not directed:
            interactions.extend(sentenceGraph.getInteractions(e2, e1))
        
        types = set()
        for interaction in interactions:
            types.add(interaction.attrib["type"])
        types = list(types)
        types.sort()
        categoryName = ""
        for name in types:
            if categoryName != "":
                categoryName += "---"
            categoryName += name
        if categoryName != "":
            return categoryName
        else:
            return "neg"           
    
    def preProcessExamples(self, allExamples):
        if "normalize" in self.styles:
            print >> sys.stderr, " Normalizing feature vectors"
            ExampleUtils.normalizeFeatureVectors(allExamples)
        return allExamples   
    
    def isPotentialGeniaInteraction(self, e1, e2):
        if e1.get("isName") == "True":
            return False
        else:
            return True
    
    def nxMultiDiGraphToUndirected(self, graph):
        undirected = NX10.MultiGraph(name=graph.name)
        undirected.add_nodes_from(graph)
        undirected.add_edges_from(graph.edges_iter())
        return undirected
    
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
            if t1 != t2 and paths.has_key(t1) and paths[t1].has_key(t2):
                pathLength = len(paths[t1][t2])
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
            interactionLengths[interaction] = (pathLength, linLength)
        return interactionLengths
        
    def getPrecedenceLevels(self, sentenceGraph, paths):
        """
        Get overlapping entity precedence
        """
        interactionLengths = self.getInteractionEdgeLengths(sentenceGraph, paths)

        interactionsByEntity = {} # Convenience mapping
        entityPrecedenceValues = {}
        for entity in sentenceGraph.entities:
            interactionsByEntity[entity] = []
            eId = entity.get("id")
            # Add access to interactions
            argDepDist = 0 # Sum of lengths of shortest paths
            argLinDist = 0 # Sum of linear distances
            for interaction in sentenceGraph.interactions:
                if interaction.get("e1") == eId: # An argument of the entity defined by the node
                    interactionsByEntity[entity].append(interaction)
                    argDepDist += interactionLengths[interaction][0]
                    argLinDist += interactionLengths[interaction][1]
            # Store precedence counts (num args, sum of dep lengths, sum of lin lengths)
            entityPrecedenceValues[entity] = (len(interactionsByEntity), argDepDist, argLinDist, entity)
        
        # Determine level of entity from precedence counts
        levelByEntity = {} # slot number
        #levelByInteraction = {} # slot number of parent node
        # There is one slot group per token, per type
        for token in sentenceGraph.tokens: # per token
            entitiesByType = {}
            for entity in sentenceGraph.tokenIsEntityHead[token]: # per type
                if entity.get("isName") == "True": # Names can never have duplicates
                    assert not levelByEntity.has_key(entity)
                    levelByEntity[entity] = 0
                    continue
                eType = entity.get("type")
                if eType == "neg":
                    continue
                if not entitiesByType.has_key(eType):
                    entitiesByType[eType] = []
                entitiesByType[eType].append(entity)
            for eType in sorted(entitiesByType.keys()):
                # Slot ordering by precedence
                sortedEntities = []
                for entity in entitiesByType[eType]:
                    sortedEntities.append(entityPrecedenceValues[entity])
                sortedEntities.sort(compareEntityPrecedence)
                level = 0
                for precedenceTuple in sortedEntities:
                    entity = precedenceTuple[3]
                    assert not levelByEntity.has_key(entity)
                    levelByEntity[entity] = level
                    # Interactions have the same slot as their parent entity
                    #for interaction in interactionsByEntity[entity]:
                    #    assert not levelByInteraction.has_key(interaction)
                    #    levelByInteraction[interaction] = level
                    level += 1
        return levelByEntity#, levelByInteraction      
            
    def buildExamples(self, sentenceGraph):
        examples = []
        exampleIndex = 0
        
        #undirected = sentenceGraph.getUndirectedDependencyGraph()
        undirected = self.nxMultiDiGraphToUndirected(sentenceGraph.dependencyGraph)
        ##undirected = sentenceGraph.dependencyGraph.to_undirected()
        ###undirected = NX10.MultiGraph(sentenceGraph.dependencyGraph) This didn't work
        paths = NX10.all_pairs_shortest_path(undirected, cutoff=999)
        
        # Determine overlapping entity precedence
        #levelByEntity, levelByInteraction = self.getPrecedenceLevels(sentenceGraph, paths)
        levelByEntity = self.getPrecedenceLevels(sentenceGraph, paths)
        
        entities = []
        # There is one entity group for each token, for each type of entity
        for token in sentenceGraph.tokens: # per token
            entitiesByType = {}
            for entity in sentenceGraph.tokenIsEntityHead[token]: # per type
                if entity.get("isName") == "True": # Names can never have duplicates
                    entities.append( (entity, 0, False) )
                    continue
                eType = entity.get("type")
                if eType == "neg":
                    continue
                if not entitiesByType.has_key(eType):
                    entitiesByType[eType] = []
                entitiesByType[eType].append(entity)
            # Create slot groups for tokens for which exists at least one entity
            eTypes = sorted(entitiesByType.keys())
            if len(eTypes) == 0:
                continue
            # Create slot groups and insert GS data there
            for eType in eTypes:
                # Use first entity of a type as the dummy entity for unfilled slots
                dummyEntity = entitiesByType[eType][0]
                # Define entity slots
                entityGroup = [None, None, None, None]
                #entityGroup = [None, None]
                # Insert existing entities into slots
                for entity in entitiesByType[eType]:
                    if levelByEntity.has_key(entity):
                        level = levelByEntity[entity]
                        if level < len(entityGroup):
                            entityGroup[level] = (entity, level, False)
                # Create dummies for potential entities
                for i in range(len(entityGroup)):
                    if entityGroup[i] == None:
                        entityGroup[i] = (dummyEntity, i, True)
                # Put all slots into one potential entity list
                #print entityGroup
                for e in entityGroup:
                    entities.append(e)
        
        # Generate examples based on interactions between entities
        for i in range(len(entities)-1):
            for j in range(i+1,len(entities)):
                eI = entities[i][0]
                eJ = entities[j][0]
                tI = sentenceGraph.entityHeadTokenByEntity[eI]
                tJ = sentenceGraph.entityHeadTokenByEntity[eJ]
                
                # define forward example
                categoryName = self.getCategoryName(sentenceGraph, entities[i], entities[j], True)
                if (not "genia_limits" in self.styles) or self.isPotentialGeniaInteraction(eI, eJ):
                    examples.append( self.buildExample(tI, tJ, paths, sentenceGraph, categoryName, exampleIndex, entities[i], entities[j]) )
                    exampleIndex += 1
                
                # define reverse
                categoryName = self.getCategoryName(sentenceGraph, entities[j], entities[i], True)
                if (not "genia_limits" in self.styles) or self.isPotentialGeniaInteraction(eJ, eI):
                    examples.append( self.buildExample(tJ, tI, paths, sentenceGraph, categoryName, exampleIndex, entities[j], entities[i]) )
                    exampleIndex += 1
        
        return examples
    
    def buildExample(self, token1, token2, paths, sentenceGraph, categoryName, exampleIndex, e1=None, e2=None):
        entity1=e1[0]
        entity2=e2[0]
        # define features
        features = {}
        features[self.featureSet.getId("gov_level")] = e1[1]
        features[self.featureSet.getId("gov_level_"+str(e1[1]))] = 1
        features[self.featureSet.getId("dep_level")] = e2[1]
        features[self.featureSet.getId("dep_level_"+str(e2[1]))] = 1
        features[self.featureSet.getId("level_pair_"+str(e1[1])+"_"+str(e2[1]))] = 1
        if True: #token1 != token2 and paths.has_key(token1) and paths[token1].has_key(token2):
            if token1 != token2 and paths.has_key(token1) and paths[token1].has_key(token2):
                path = paths[token1][token2]
            else:
                path = [token1, token2]
            assert(self.pathLengths == None)
            if self.pathLengths == None or len(path)-1 in self.pathLengths:
                if not "no_dependency" in self.styles:
                    if token1 != token2 and paths.has_key(token1) and paths[token1].has_key(token2):
                        edges = self.multiEdgeFeatureBuilder.getEdges(sentenceGraph.dependencyGraph, path)
                    else:
                        edges = None
                if "entity_type" in self.styles:
                    features[self.featureSet.getId("e1_"+entity1.attrib["type"])] = 1
                    features[self.featureSet.getId("e2_"+entity2.attrib["type"])] = 1
                    features[self.featureSet.getId("distance_"+str(len(path)))] = 1
                if not "no_dependency" in self.styles:
                    self.multiEdgeFeatureBuilder.setFeatureVector(features, entity1, entity2)
                    #self.multiEdgeFeatureBuilder.buildStructureFeatures(sentenceGraph, paths) # remove for fast
                    if not "disable_entity_features" in self.styles:
                        self.multiEdgeFeatureBuilder.buildEntityFeatures(sentenceGraph)
                    self.multiEdgeFeatureBuilder.buildPathLengthFeatures(path)
                    if not "disable_terminus_features" in self.styles:
                        self.multiEdgeFeatureBuilder.buildTerminusTokenFeatures(path, sentenceGraph) # remove for fast
                    if not "disable_single_element_features" in self.styles:
                        self.multiEdgeFeatureBuilder.buildSingleElementFeatures(path, edges, sentenceGraph)
                    if not "disable_ngram_features" in self.styles:
                        self.multiEdgeFeatureBuilder.buildPathGrams(2, path, edges, sentenceGraph) # remove for fast
                        self.multiEdgeFeatureBuilder.buildPathGrams(3, path, edges, sentenceGraph) # remove for fast
                        self.multiEdgeFeatureBuilder.buildPathGrams(4, path, edges, sentenceGraph) # remove for fast
                    #self.buildEdgeCombinations(path, edges, sentenceGraph, features) # remove for fast
                    #if edges != None:
                    #    self.multiEdgeFeatureBuilder.buildTerminusFeatures(path[0], edges[0][1]+edges[1][0], "t1", sentenceGraph) # remove for fast
                    #    self.multiEdgeFeatureBuilder.buildTerminusFeatures(path[-1], edges[len(path)-1][len(path)-2]+edges[len(path)-2][len(path)-1], "t2", sentenceGraph) # remove for fast
                    if not "disable_path_edge_features" in self.styles:
                        self.multiEdgeFeatureBuilder.buildPathEdgeFeatures(path, edges, sentenceGraph)
                    self.multiEdgeFeatureBuilder.buildSentenceFeatures(sentenceGraph)
                    self.multiEdgeFeatureBuilder.setFeatureVector(None)
                if not "no_linear" in self.styles:
                    self.tokenFeatureBuilder.setFeatureVector(features)
                    for i in range(len(sentenceGraph.tokens)):
                        if sentenceGraph.tokens[i] == token1:
                            token1Index = i
                        if sentenceGraph.tokens[i] == token2:
                            token2Index = i
                    linearPreTag = "linfw_"
                    if token1Index > token2Index: 
                        token1Index, token2Index = token2Index, token1Index
                        linearPreTag = "linrv_"
                    self.tokenFeatureBuilder.buildLinearOrderFeatures(token1Index, sentenceGraph, 2, 2, preTag="linTok1")
                    self.tokenFeatureBuilder.buildLinearOrderFeatures(token2Index, sentenceGraph, 2, 2, preTag="linTok2")
                    # Before, middle, after
    #                self.tokenFeatureBuilder.buildTokenGrams(0, token1Index-1, sentenceGraph, "bf")
    #                self.tokenFeatureBuilder.buildTokenGrams(token1Index+1, token2Index-1, sentenceGraph, "bw")
    #                self.tokenFeatureBuilder.buildTokenGrams(token2Index+1, len(sentenceGraph.tokens)-1, sentenceGraph, "af")
                    # before-middle, middle, middle-after
#                    self.tokenFeatureBuilder.buildTokenGrams(0, token2Index-1, sentenceGraph, linearPreTag+"bf", max=2)
#                    self.tokenFeatureBuilder.buildTokenGrams(token1Index+1, token2Index-1, sentenceGraph, linearPreTag+"bw", max=2)
#                    self.tokenFeatureBuilder.buildTokenGrams(token1Index+1, len(sentenceGraph.tokens)-1, sentenceGraph, linearPreTag+"af", max=2)
                    self.tokenFeatureBuilder.setFeatureVector(None)
                if "random" in self.styles:
                    self.randomFeatureBuilder.setFeatureVector(features)
                    self.randomFeatureBuilder.buildRandomFeatures(100, 0.01)
                    self.randomFeatureBuilder.setFeatureVector(None)
                if "genia_limits" in self.styles:
                    e1Type = entity1.get("type")
                    e2Type = entity2.get("type")
                    assert(entity1.get("isName") == "False")
                    if entity2.get("isName") == "True":
                        features[self.featureSet.getId("GENIA_target_protein")] = 1
                    else:
                        features[self.featureSet.getId("GENIA_nested_event")] = 1
                    if e1Type.find("egulation") != -1: # leave r out to avoid problems with capitalization
                        if entity2.get("isName") == "True":
                            features[self.featureSet.getId("GENIA_regulation_of_protein")] = 1
                        else:
                            features[self.featureSet.getId("GENIA_regulation_of_event")] = 1
            else:
                features[self.featureSet.getId("always_negative")] = 1
                if "subset" in self.styles:
                    features[self.featureSet.getId("out_of_scope")] = 1
        else:
            features[self.featureSet.getId("always_negative")] = 1
            if "subset" in self.styles:
                features[self.featureSet.getId("out_of_scope")] = 1
            path = [token1, token2]
        # define extra attributes
        if int(path[0].attrib["id"].split("_")[-1]) < int(path[-1].attrib["id"].split("_")[-1]):
            #extra = {"xtype":"edge","type":"i","t1":path[0],"t2":path[-1]}
            extra = {"xtype":"ue","type":"i","t1":path[0].get("id"),"t2":path[-1].get("id")}
            extra["deprev"] = False
        else:
            #extra = {"xtype":"edge","type":"i","t1":path[-1],"t2":path[0]}
            extra = {"xtype":"ue","type":"i","t1":path[-1].get("id"),"t2":path[0].get("id")}
            extra["deprev"] = True
        if entity1 != None:
            extra["e1"] = entity1.get("id")
            extra["l1"] = str(e1[1])
            extra["d1"] = str(e1[2])[0] # is a dummy node (an entity not in existing triggers)
        if entity2 != None:
            extra["e2"] = entity2.get("id")
            extra["l2"] = str(e2[1])
            extra["d2"] = str(e2[2])[0] # is a dummy node (an entity not in existing triggers)
        extra["categoryName"] = categoryName
        sentenceOrigId = sentenceGraph.sentenceElement.get("origId")
        if sentenceOrigId != None:
            extra["SOID"] = sentenceOrigId       
        # make example
        if "binary" in self.styles:
            if categoryName != "neg":
                category = 1
            else:
                category = -1
            categoryName = "i"
        else:
            category = self.classSet.getId(categoryName)
        
        return (sentenceGraph.getSentenceId()+".x"+str(exampleIndex),category,features,extra)