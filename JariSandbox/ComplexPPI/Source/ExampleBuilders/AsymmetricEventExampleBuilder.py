"""
Edge Examples
"""
__version__ = "$Revision: 1.2 $"

import sys, os
import random
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
from ExampleStats import ExampleStats
from Filters.POSPairGazetteer import POSPairGazetteer
import Graph.networkx_v10rc1 as NX10
#IF LOCAL
import Utils.BioInfer.OntologyUtils as OntologyUtils
#ENDIF

class AsymmetricEventExampleBuilder(ExampleBuilder):
    def __init__(self, style=["typed","directed"], length=None, types=[], featureSet=None, classSet=None):
        if featureSet == None:
            featureSet = IdSet()
        if classSet == None:
            classSet = IdSet(1)
        else:
            classSet = classSet
        assert( classSet.getId("neg") == 1 )
        
        ExampleBuilder.__init__(self, classSet=classSet, featureSet=featureSet)
        if style.find(",") != -1:
            style = style.split(",")
        self.styles = style
        
        self.negFrac = None
        self.posPairGaz = POSPairGazetteer()
        for s in style:
            if s.find("negFrac") != -1:      
                self.negFrac = float(s.split("_")[-1])
                print >> sys.stderr, "Downsampling negatives to", self.negFrac
                self.negRand = random.Random(15)
            elif s.find("posPairGaz") != -1:
                self.posPairGaz = POSPairGazetteer(loadFrom=s.split("_", 1)[-1])
        
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
        classSet, featureSet = cls.getIdSets(idFileTag)
        if style != None:
            e = cls(style=style, classSet=classSet, featureSet=featureSet)
        else:
            e = cls(classSet=classSet, featureSet=featureSet)
        sentences = cls.getSentences(input, parse, tokenization)
        e.buildExamplesForSentences(sentences, output, idFileTag)
        if "printClassIds" in e.styles:
            print >> sys.stderr, e.classSet.Ids
  
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
        types = set()
        themeE1Types = set()
        intEdges = []
        if sentenceGraph.interactionGraph.has_edge(t1, t2):
            intEdges = sentenceGraph.interactionGraph.get_edge_data(t1, t2, default={})
            # NOTE: Only works if keys are ordered integers
            for i in range(len(intEdges)):
                types.add(intEdges[i]["element"].get("type"))

#        if (not directed) and sentenceGraph.interactionGraph.has_edge(t2, t1):
#            intEdgesReverse = sentenceGraph.interactionGraph.get_edge(t2, t1, default={})
#            # NOTE: Only works if keys are ordered integers
#            for i in range(len(intEdgesReverse)):
#                intElement = intEdgesReverse[i]["element"]
#                intType = intElement.get("type")
#                types.add(intType)
#            intEdges.extend(intEdgesReverse)

        for i in range(len(intEdges)):
            intElement = intEdges[i]["element"]
            intType = intElement.get("type")
            if intType == "Theme":
                e1Entity = sentenceGraph.entitiesById[intElement.get("e1")]
                themeE1Types.add(e1Entity.get("type"))
            #types.add(intType)
        
        if len(themeE1Types) != 0:
            themeE1Types = list(themeE1Types)
            themeE1Types.sort()
            categoryName = ""
            for name in themeE1Types:
                if categoryName != "":
                    categoryName += "---"
                categoryName += name
            return categoryName            
        else:
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
        if e1.get("isName") == "True":
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
            
    def buildExamples(self, sentenceGraph):
        examples = []
        exampleIndex = 0
        
        clearGraph = sentenceGraph.getCleared()
        
        #undirected = sentenceGraph.getUndirectedDependencyGraph()
        undirected = self.nxMultiDiGraphToUndirected(sentenceGraph.dependencyGraph)
        ##undirected = sentenceGraph.dependencyGraph.to_undirected()
        ###undirected = NX10.MultiGraph(sentenceGraph.dependencyGraph) This didn't work
        paths = NX10.all_pairs_shortest_path(undirected, cutoff=999)
        
        # Generate examples based on interactions between entities or interactions between tokens
        if "entities" in self.styles:
            loopRange = len(sentenceGraph.entities)
        else:
            loopRange = len(sentenceGraph.tokens)
        #for i in range(loopRange-1):
        for i in range(loopRange): # allow self-interactions
            #for j in range(i+1,loopRange):
            for j in range(i,loopRange): # allow self-interactions
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
#                # only consider paths between entities (NOTE! entities, not only named entities)
#                if "headsOnly" in self.styles:
#                    if (len(sentenceGraph.tokenIsEntityHead[tI]) == 0) or (len(sentenceGraph.tokenIsEntityHead[tJ]) == 0):
#                        continue
                
                if "directed" in self.styles:
                    # define forward
                    if "entities" in self.styles:
                        categoryName = self.getCategoryName(sentenceGraph, eI, eJ, True)
                    else:
                        categoryName = self.getCategoryNameFromTokens(sentenceGraph, tI, tJ, True)
                    self.exampleStats.beginExample(categoryName)
                    if self.negFrac == None or categoryName != "neg" or (categoryName == "neg" and self.negRand.random() < self.negFrac):
                        makeExample = True
                        if ("genia_limits" in self.styles) and not self.isPotentialGeniaInteraction(eI, eJ):
                            makeExample = False
                            self.exampleStats.filter("genia_limits")
                        if self.posPairGaz.getNegFrac((tI.get("POS"), tJ.get("POS"))) == 1.0:
                            makeExample = False
                            self.exampleStats.filter("pos_pair")
                        if makeExample:
                            if not sentenceGraph.tokenIsName[tI]:
                                examples.append( self.buildExample(tI, tJ, paths, clearGraph, categoryName, exampleIndex, eI, eJ) )
                                exampleIndex += 1
                            else:
                                self.exampleStats.filter("genia_token_limits")
                    else:
                        self.exampleStats.filter("neg_frac")
                    self.exampleStats.endExample()
                    
                    # define reverse
                    if "entities" in self.styles:
                        categoryName = self.getCategoryName(sentenceGraph, eJ, eI, True)
                    else:
                        categoryName = self.getCategoryNameFromTokens(sentenceGraph, tJ, tI, True)
                    self.exampleStats.beginExample(categoryName)
                    if self.negFrac == None or categoryName != "neg" or (categoryName == "neg" and self.negRand.random() < self.negFrac):
                        makeExample = True
                        if ("genia_limits" in self.styles) and not self.isPotentialGeniaInteraction(eJ, eI):
                            makeExample = False
                            self.exampleStats.filter("genia_limits")
                        if ("bioinfer_limits" in self.styles) and not self.isPotentialBioInferInteraction(eJ, eI, categoryName):
                            makeExample = False
                            self.exampleStats.filter("bioinfer_limits")
                        if self.posPairGaz.getNegFrac((tJ.get("POS"), tI.get("POS"))) == 1.0:
                            makeExample = False
                            self.exampleStats.filter("pos_pair")
                        if makeExample:
                            if not sentenceGraph.tokenIsName[tJ]:
                                examples.append( self.buildExample(tJ, tI, paths, clearGraph, categoryName, exampleIndex, eJ, eI) )
                                exampleIndex += 1
                            else:
                                self.exampleStats.filter("genia_token_limits")
                    else:
                        self.exampleStats.filter("neg_frac")
                    self.exampleStats.endExample()
#                else:
#                    if "entities" in self.styles:
#                        categoryName = self.getCategoryName(sentenceGraph, eI, eJ, False)
#                    else:
#                        categoryName = self.getCategoryNameFromTokens(sentenceGraph, tI, tJ, False)
#                    forwardExample = self.buildExample(tI, tJ, paths, clearGraph, categoryName, exampleIndex, eI, eJ)
#                    if not "graph_kernel" in self.styles:
#                        reverseExample = self.buildExample(tJ, tI, paths, clearGraph, categoryName, exampleIndex, eJ, eI)
#                        forwardExample[2].update(reverseExample[2])
#                    examples.append(forwardExample)
#                    exampleIndex += 1
        
        return examples
    
    def buildExample(self, token1, token2, paths, sentenceGraph, categoryName, exampleIndex, entity1=None, entity2=None):
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
                    if token1 == token2:
                        features[self.featureSet.getId("tokenSelfLoop")] = 1
                    
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
#        if int(path[0].attrib["id"].split("_")[-1]) < int(path[-1].attrib["id"].split("_")[-1]):
#            #extra = {"xtype":"edge","type":"i","t1":path[0],"t2":path[-1]}
#            extra = {"xtype":"asym","type":"i","t1":path[0].get("id"),"t2":path[-1].get("id")}
#            extra["deprev"] = False
#        else:
#            #extra = {"xtype":"edge","type":"i","t1":path[-1],"t2":path[0]}
#            extra = {"xtype":"asym","type":"i","t1":path[-1].get("id"),"t2":path[0].get("id")}
#            extra["deprev"] = True

        extra = {"xtype":"asym","type":"i","t1":token1.get("id"),"t2":token2.get("id")}
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