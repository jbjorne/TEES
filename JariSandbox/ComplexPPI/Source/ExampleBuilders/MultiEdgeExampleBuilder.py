"""
Edge Examples
"""
__version__ = "$Revision: 1.47 $"

import sys, os
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
from FeatureBuilders.TriggerFeatureBuilder import TriggerFeatureBuilder
#IF LOCAL
import Utils.BioInfer.OntologyUtils as OntologyUtils
#ENDIF

class MultiEdgeExampleBuilder(ExampleBuilder):
    """
    This example builder makes edge examples, i.e. examples describing
    the event arguments.
    """
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
        if "graph_kernel" in self.styles:
            from FeatureBuilders.GraphKernelFeatureBuilder import GraphKernelFeatureBuilder
            self.graphKernelFeatureBuilder = GraphKernelFeatureBuilder(self.featureSet)
        if "noAnnType" in self.styles:
            self.multiEdgeFeatureBuilder.noAnnType = True
        if "noMasking" in self.styles:
            self.multiEdgeFeatureBuilder.maskNamedEntities = False
        if "maxFeatures" in self.styles:
			self.multiEdgeFeatureBuilder.maximum = True
        self.tokenFeatureBuilder = TokenFeatureBuilder(self.featureSet)
        if "ontology" in self.styles:
            self.multiEdgeFeatureBuilder.ontologyFeatureBuilder = BioInferOntologyFeatureBuilder(self.featureSet)
        if "nodalida" in self.styles:
            self.nodalidaFeatureBuilder = NodalidaFeatureBuilder(self.featureSet)
        #IF LOCAL
        if "bioinfer_limits" in self.styles:
            self.bioinferOntologies = OntologyUtils.getBioInferTempOntology()
        if "trigger_features" in self.styles:
            self.triggerFeatureBuilder = TriggerFeatureBuilder(self.featureSet)
            self.triggerFeatureBuilder.useNonNameEntities = True
            #self.bioinferOntologies = OntologyUtils.loadOntologies(OntologyUtils.g_bioInferFileName)
        #ENDIF
        self.pathLengths = length
        assert(self.pathLengths == None)
        self.types = types
        if "random" in self.styles:
            from FeatureBuilders.RandomFeatureBuilder import RandomFeatureBuilder
            self.randomFeatureBuilder = RandomFeatureBuilder(self.featureSet)
        
        #self.outFile = open("exampleTempFile.txt","wt")

    @classmethod
    def run(cls, input, output, parse, tokenization, style, idFileTag=None):
        """
        An interface for running the example builder without needing to create a class
        """
        classSet, featureSet = cls.getIdSets(idFileTag)
        if style != None:
            e = MultiEdgeExampleBuilder(style=style, classSet=classSet, featureSet=featureSet)
        else:
            e = MultiEdgeExampleBuilder(classSet=classSet, featureSet=featureSet)
        sentences = cls.getSentences(input, parse, tokenization)
        #e.buildExamplesForSentences(sentences, output, idFileTag)
        e.buildExamplesForSentencesSeparateGold(sentences, sentences, output, idFileTag)

    @classmethod
    def runNew(cls, input, gold, output, parse, tokenization, style, idFileTag=None):
        """
        An interface for running the example builder without needing to create a class
        """
        classSet, featureSet = cls.getIdSets(idFileTag)
        if style != None:
            e = MultiEdgeExampleBuilder(style=style, classSet=classSet, featureSet=featureSet)
        else:
            e = MultiEdgeExampleBuilder(classSet=classSet, featureSet=featureSet)
        sentences = cls.getSentences(input, parse, tokenization)
        if gold != None:
            goldSentences = cls.getSentences(gold, parse, tokenization)
        else:
            goldSentences = None
        e.buildExamplesForSentencesSeparateGold(sentences, goldSentences, output, idFileTag)
    
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
    
    def getCategoryNameFromTokens(self, sentenceGraph, t1, t2, directed=True):
        """
        Example class. Multiple overlapping edges create a merged type.
        """
        types = set()
        if sentenceGraph.interactionGraph.has_edge(t1, t2):
            intEdges = sentenceGraph.interactionGraph.get_edge_data(t1, t2, default={})
            # NOTE: Only works if keys are ordered integers
            for i in range(len(intEdges)):
                types.add(intEdges[i]["element"].get("type"))
        if (not directed) and sentenceGraph.interactionGraph.has_edge(t2, t1):
            intEdges = sentenceGraph.interactionGraph.get_edge(t2, t1, default={})
            # NOTE: Only works if keys are ordered integers
            for i in range(len(intEdges)):
                types.add(intEdges[i]["element"].get("type"))
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
        
    def getCategoryName(self, sentenceGraph, e1, e2, directed=True):
        """
        Example class. Multiple overlapping edges create a merged type.
        """
        if e1 == None or e2 == None:
            return "neg" 
        
        interactions = sentenceGraph.getInteractions(e1, e2)
        if not directed:
            interactions.extend(sentenceGraph.getInteractions(e2, e1))
        
        types = set()
        for interaction in interactions:
            iType = interaction.get("type")
            if iType != None:
                if "themeOnly" in self.styles and iType != "Theme":
                    continue
                types.add(iType)
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
        # Duplicates cannot be removed here, as they should only be removed from the training set. This is done
        # in the classifier.
#        if "no_duplicates" in self.styles:
#            count = len(allExamples)
#            print >> sys.stderr, " Removing duplicates,", 
#            allExamples = ExampleUtils.removeDuplicates(allExamples)
#            print >> sys.stderr, "removed", count - len(allExamples)
        if "normalize" in self.styles:
            print >> sys.stderr, " Normalizing feature vectors"
            ExampleUtils.normalizeFeatureVectors(allExamples)
        return allExamples   
    
    def isPotentialGeniaInteraction(self, e1, e2):
        """
        Genia named entities can never act as event triggers, so
        edges can't leave from them. We can reduce the number of 
        examples generated by removing these always negative cases.
        """
        if "causeAfterTheme" in self.styles:
            if e1.get("type") in ["Regulation", "Positive_regulation", "Negative_regulation"]:
                return True
        else:
            # Normal
            if e1.get("isName") == "True" and e2.get("isName") == "True":
                return False
            elif e1.get("isName") == "True" and e2.get("isName") == "False":
                return False
            # Only a protein can be a Theme for a non-regulation event
            elif e1.get("isName") == "False" and e1.get("type").find("egulation") == -1 and e2.get("isName") == "False":
                return False
            else:
                return True
    
    #IF LOCAL
    def getBioInferParentType(self, eType):
        if eType == "Physical_entity" or OntologyUtils.hasParent(eType, "Physical_entity", self.bioinferOntologies):
            return "Physical"
        elif eType == "Property_entity" or OntologyUtils.hasParent(eType, "Property_entity", self.bioinferOntologies):
            return "Property"
        elif OntologyUtils.hasParent(eType, "Relationship", self.bioinferOntologies):
            return "Process"
        else:
            assert False, eType
        
#        if self.bioinferOntologies["Entity"].has_key(eType):
#            if OntologyUtils.hasParent(eType, "Physical_entity", self.bioinferOntologies):
#                assert not OntologyUtils.hasParent(eType, "Property_entity", self.bioinferOntologies), eType
#                return "Physical"
#            else:
#                assert OntologyUtils.hasParent(eType, "Property_entity", self.bioinferOntologies), eType
#                return "Property"
#                
#        else:
#            assert self.bioinferOntologies.has_key(eType), eType
#            #assert OntologyUtils.hasParent(eType, "Process_entity", self.bioinferOntologies["Relationship"]), eType
#            return "Process"
    
    def isPotentialBioInferInteraction(self, e1, e2, categoryName):
        e1Type = self.getBioInferParentType(e1.get("type"))
        e2Type = self.getBioInferParentType(e2.get("type"))
        if e1Type == "Process" or e1Type == "Property":
            return True
        elif e1Type == "Physical" and e2Type == "Physical":
            return True
        elif e1Type == "Physical" and e2Type == "Process": # hack
            return True
        else:
            assert(categoryName == "neg"), categoryName + " category for " + e1Type + " and " + e2Type
            return False
    #ENDIF
    
    def nxMultiDiGraphToUndirected(self, graph):
        undirected = NX10.MultiGraph(name=graph.name)
        undirected.add_nodes_from(graph)
        undirected.add_edges_from(graph.edges_iter())
        return undirected
            
    def buildExamples(self, sentenceGraph, goldGraph):
        """
        Build examples for a single sentence. Returns a list of examples.
        See Core/ExampleUtils for example format.
        """
        examples = []
        exampleIndex = 0
        
        if "trigger_features" in self.styles: 
            self.triggerFeatureBuilder.initSentence(sentenceGraph)
        
        #if "causeAfterTheme" in self.styles:
        #    self.edgeTypesForFeatures = ["Theme"]
        #else:
        #    self.edgeTypesForFeatures = []
        
        #undirected = sentenceGraph.getUndirectedDependencyGraph()
        undirected = self.nxMultiDiGraphToUndirected(sentenceGraph.dependencyGraph)
        ##undirected = sentenceGraph.dependencyGraph.to_undirected()
        ###undirected = NX10.MultiGraph(sentenceGraph.dependencyGraph) This didn't work
        paths = NX10.all_pairs_shortest_path(undirected, cutoff=999)
        
        # sentenceGraph -> goldGraph mappings
        entityToGoldEntity = {}
        for entity in sentenceGraph.entities:
            entityToGoldEntity[entity] = None
        if goldGraph != None:
            # Check graph consistency
            for i in range(len(sentenceGraph.tokens)):
                token = sentenceGraph.tokens[i]
                goldToken = goldGraph.tokens[i]
                assert token.get("id") == goldToken.get("id") and token.get("charOffset") == goldToken.get("charOffset")
            # Map entities to gold entities
            for entity in sentenceGraph.entities:
                if entity.get("type") == "neg":
                    continue
                for goldEntity in goldGraph.entities:
                    if entity.get("headOffset") == goldEntity.get("headOffset") and entity.get("type") == goldEntity.get("type"):
                        entityToGoldEntity[entity] = goldEntity
                        break
        
        # Generate examples based on interactions between entities or interactions between tokens
        if "entities" in self.styles:
            loopRange = len(sentenceGraph.entities)
        else:
            loopRange = len(sentenceGraph.tokens)
        for i in range(loopRange-1):
            for j in range(i+1,loopRange):
                eI = None
                eJ = None
                if "entities" in self.styles:
                    eI = sentenceGraph.entities[i]
                    eJ = sentenceGraph.entities[j]
                    tI = sentenceGraph.entityHeadTokenByEntity[eI]
                    tJ = sentenceGraph.entityHeadTokenByEntity[eJ]
                    #if "no_ne_interactions" in self.styles and eI.get("isName") == "True" and eJ.get("isName") == "True":
                    #    continue
                    if eI.get("type") == "neg" or eJ.get("type") == "neg":
                        continue
                else:
                    tI = sentenceGraph.tokens[i]
                    tJ = sentenceGraph.tokens[j]
                # only consider paths between entities (NOTE! entities, not only named entities)
                if "headsOnly" in self.styles:
                    if (len(sentenceGraph.tokenIsEntityHead[tI]) == 0) or (len(sentenceGraph.tokenIsEntityHead[tJ]) == 0):
                        continue                        
                
                if "directed" in self.styles:
                    # define forward ######################
                    if "entities" in self.styles:
                        categoryName = self.getCategoryName(goldGraph, entityToGoldEntity[eI], entityToGoldEntity[eJ], True)
                    else:
                        categoryName = self.getCategoryNameFromTokens(sentenceGraph, tI, tJ, True)
                    if (not "genia_limits" in self.styles) or self.isPotentialGeniaInteraction(eI, eJ):
                        examples.append( self.buildExample(tI, tJ, paths, sentenceGraph, categoryName, exampleIndex, eI, eJ) )
                        exampleIndex += 1
                    # define reverse #######################
                    if "entities" in self.styles:
                        categoryName = self.getCategoryName(goldGraph, entityToGoldEntity[eJ], entityToGoldEntity[eI], True)
                    else:
                        categoryName = self.getCategoryNameFromTokens(sentenceGraph, tJ, tI, True)
                    makeExample = True
                    if ("genia_limits" in self.styles) and not self.isPotentialGeniaInteraction(eJ, eI):
                        makeExample = False
                    if ("bioinfer_limits" in self.styles) and not self.isPotentialBioInferInteraction(eJ, eI, categoryName):
                        makeExample = False
                    if "causeAfterTheme" in self.styles:
                        sourceCategoryName = self.getCategoryName(sentenceGraph, eJ, eI, True)
                        if sourceCategoryName == "Theme":
                            makeExample = False
                        elif categoryName != "Cause":
                            categoryName = "neg"
                    elif "themeOnly" in self.styles:
                        if categoryName != "Theme":
                            categoryName = "neg"
                    if makeExample:
                        examples.append( self.buildExample(tJ, tI, paths, sentenceGraph, categoryName, exampleIndex, eJ, eI) )
                        exampleIndex += 1
                else:
                    if "entities" in self.styles:
                        categoryName = self.getCategoryName(goldGraph, entityToGoldEntity[eI], entityToGoldEntity[eJ], False)
                    else:
                        categoryName = self.getCategoryNameFromTokens(sentenceGraph, tI, tJ, False)
                    forwardExample = self.buildExample(tI, tJ, paths, sentenceGraph, categoryName, exampleIndex, eI, eJ)
                    if not "graph_kernel" in self.styles:
                        reverseExample = self.buildExample(tJ, tI, paths, sentenceGraph, categoryName, exampleIndex, eJ, eI)
                        forwardExample[2].update(reverseExample[2])
                    examples.append(forwardExample)
                    exampleIndex += 1
        
        return examples
    
    def buildExample(self, token1, token2, paths, sentenceGraph, categoryName, exampleIndex, entity1=None, entity2=None):
        """
        Build a single directed example for the potential edge between token1 and token2
        """
        # define features
        features = {}
        if True: #token1 != token2 and paths.has_key(token1) and paths[token1].has_key(token2):
            if token1 != token2 and paths.has_key(token1) and paths[token1].has_key(token2):
                path = paths[token1][token2]
            else:
                path = [token1, token2]
            assert(self.pathLengths == None)
            if self.pathLengths == None or len(path)-1 in self.pathLengths:
#                if not "no_ontology" in self.styles:
#                    self.ontologyFeatureBuilder.setFeatureVector(features)
#                    self.ontologyFeatureBuilder.buildOntologyFeaturesForPath(sentenceGraph, path)
#                    self.ontologyFeatureBuilder.setFeatureVector(None)
                if "trigger_features" in self.styles: # F 85.52 -> 85.55
                    self.triggerFeatureBuilder.setFeatureVector(features)
                    self.triggerFeatureBuilder.tag = "trg1_"
                    self.triggerFeatureBuilder.buildFeatures(token1)
                    self.triggerFeatureBuilder.tag = "trg2_"
                    self.triggerFeatureBuilder.buildFeatures(token2)
                    self.triggerFeatureBuilder.setFeatureVector(None)
                if "causeAfterTheme" in self.styles:
                    e1Id = entity1.get("id")
                    e2Id = entity2.get("id")
                    e1ThemeInCount = 0
                    e1ThemeOutCount = 0
                    e2ThemeInCount = 0
                    e2ThemeOutCount = 0
                    for interaction in sentenceGraph.interactions:
                        if interaction.get("type") != "Theme":
                            continue
                        if interaction.get("e1") == e1Id:
                            e1ThemeOutCount += 1
                        if interaction.get("e2") == e1Id:
                            e1ThemeInCount += 1
                        if interaction.get("e1") == e2Id:
                            e2ThemeOutCount += 1
                        if interaction.get("e2") == e2Id:
                            e2ThemeInCount += 1
                    features[self.featureSet.getId("e1ThemeInCount")] = e1ThemeInCount
                    features[self.featureSet.getId("e1ThemeInCount_"+str(e1ThemeInCount))] = 1
                    features[self.featureSet.getId("e1ThemeOutCount")] = e1ThemeOutCount
                    features[self.featureSet.getId("e1ThemeOutCount_"+str(e1ThemeOutCount))] = 1
                    features[self.featureSet.getId("e2ThemeInCount")] = e2ThemeInCount
                    features[self.featureSet.getId("e2ThemeInCount_"+str(e2ThemeInCount))] = 1
                    features[self.featureSet.getId("e2ThemeOutCount")] = e2ThemeOutCount
                    features[self.featureSet.getId("e2ThemeOutCount_"+str(e2ThemeOutCount))] = 1
                if "graph_kernel" in self.styles or not "no_dependency" in self.styles:
                    if token1 != token2 and paths.has_key(token1) and paths[token1].has_key(token2):
                        edges = self.multiEdgeFeatureBuilder.getEdges(sentenceGraph.dependencyGraph, path)
                    else:
                        edges = None
                if "graph_kernel" in self.styles:
                    self.graphKernelFeatureBuilder.setFeatureVector(features, entity1, entity2)
                    self.graphKernelFeatureBuilder.buildGraphKernelFeatures(sentenceGraph, path, edges)
                    self.graphKernelFeatureBuilder.setFeatureVector(None)
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
                if "nodalida" in self.styles:
                    self.nodalidaFeatureBuilder.setFeatureVector(features, entity1, entity2)
                    shortestPaths = self.nodalidaFeatureBuilder.buildShortestPaths(sentenceGraph.dependencyGraph, path)
                    print shortestPaths
                    if len(shortestPaths) > 0:
                        self.nodalidaFeatureBuilder.buildNGrams(shortestPaths, sentenceGraph)
                    self.nodalidaFeatureBuilder.setFeatureVector(None)
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
            extra = {"xtype":"edge","type":"i","t1":path[0].get("id"),"t2":path[-1].get("id")}
            extra["deprev"] = False
        else:
            #extra = {"xtype":"edge","type":"i","t1":path[-1],"t2":path[0]}
            extra = {"xtype":"edge","type":"i","t1":path[-1].get("id"),"t2":path[0].get("id")}
            extra["deprev"] = True
        if entity1 != None:
            #extra["e1"] = entity1
            extra["e1"] = entity1.get("id")
        if entity2 != None:
            #extra["e2"] = entity2
            extra["e2"] = entity2.get("id")
        extra["categoryName"] = categoryName
        sentenceOrigId = sentenceGraph.sentenceElement.get("origId")
        if sentenceOrigId != None:
            extra["SOID"] = sentenceOrigId
        if "causeAfterTheme" in self.styles:
            extra["causeAfterTheme"] = "True"     
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