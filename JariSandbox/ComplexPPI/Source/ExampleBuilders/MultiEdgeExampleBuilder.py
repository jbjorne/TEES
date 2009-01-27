import sys
sys.path.append("..")
from Core.ExampleBuilder import ExampleBuilder
from Core.IdSet import IdSet
import Core.ExampleUtils as ExampleUtils
from FeatureBuilders.MultiEdgeFeatureBuilder import MultiEdgeFeatureBuilder
from FeatureBuilders.TokenFeatureBuilder import TokenFeatureBuilder
from FeatureBuilders.BioInferOntologyFeatureBuilder import BioInferOntologyFeatureBuilder
from FeatureBuilders.NodalidaFeatureBuilder import NodalidaFeatureBuilder
import networkx as NX

class MultiEdgeExampleBuilder(ExampleBuilder):
    def __init__(self, style=["typed","directed","headsOnly"], length=None, types=[]):
        ExampleBuilder.__init__(self)
        self.styles = style
        self.classSet = IdSet(1)
        assert( self.classSet.getId("neg") == 1 )
        self.multiEdgeFeatureBuilder = MultiEdgeFeatureBuilder(self.featureSet)
        if "graph_kernel" in self.styles:
            from FeatureBuilders.GraphKernelFeatureBuilder import GraphKernelFeatureBuilder
            self.graphKernelFeatureBuilder = GraphKernelFeatureBuilder(self.featureSet)
        if "noAnnType" in self.styles:
            self.multiEdgeFeatureBuilder.noAnnType = True
        if "maxFeatures" in self.styles:
			self.multiEdgeFeatureBuilder.maximum = True
        self.tokenFeatureBuilder = TokenFeatureBuilder(self.featureSet)
        if "ontology" in self.styles:
            self.multiEdgeFeatureBuilder.ontologyFeatureBuilder = BioInferOntologyFeatureBuilder(self.featureSet)
        if "nodalida" in self.styles:
            self.nodalidaFeatureBuilder = NodalidaFeatureBuilder(self.featureSet)
        self.pathLengths = length
        self.types = types
        if "random" in self.styles:
            from FeatureBuilders.RandomFeatureBuilder import RandomFeatureBuilder
            self.randomFeatureBuilder = RandomFeatureBuilder(self.featureSet)
        
        #self.outFile = open("exampleTempFile.txt","wt")
    
    def filterEdgesByType(self, edges, typesToInclude):
        if len(typesToInclude) == 0:
            return edges
        edgesToKeep = []
        for edge in edges:
            if edge.attrib["type"] in typesToInclude:
                edgesToKeep.append(edge)
        return edgesToKeep
    
    def getCategoryNameFromTokens(self, sentenceGraph, t1, t2, directed=True):
        types = set()
        if sentenceGraph.interactionGraph.has_edge(t1, t2):
            intEdges = sentenceGraph.interactionGraph.get_edge(t1, t2)
            for intEdge in intEdges:
                types.add(intEdge.attrib["type"])
        if (not directed) and sentenceGraph.interactionGraph.has_edge(t2, t1):
            intEdges = sentenceGraph.interactionGraph.get_edge(t2, t1)
            for intEdge in intEdges:
                types.add(intEdge.attrib["type"])
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
                        
    def buildExamples(self, sentenceGraph):
        examples = []
        exampleIndex = 0
        
        undirected = sentenceGraph.dependencyGraph.to_undirected()
        paths = NX.all_pairs_shortest_path(undirected, cutoff=999)
        
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
                else:
                    tI = sentenceGraph.tokens[i]
                    tJ = sentenceGraph.tokens[j]
                # only consider paths between entities (NOTE! entities, not only named entities)
                if "headsOnly" in self.styles:
                    if (len(sentenceGraph.tokenIsEntityHead[tI]) == 0) or (len(sentenceGraph.tokenIsEntityHead[tJ]) == 0):
                        continue
                
                if "directed" in self.styles:
                    # define forward
                    if "entities" in self.styles:
                        categoryName = self.getCategoryName(sentenceGraph, eI, eJ, True)
                    else:
                        categoryName = self.getCategoryNameFromTokens(sentenceGraph, tI, tJ, True)
                    examples.append( self.buildExample(tI, tJ, paths, sentenceGraph, categoryName, exampleIndex, eI, eJ) )
                    exampleIndex += 1
                    # define reverse
                    if "entities" in self.styles:
                        categoryName = self.getCategoryName(sentenceGraph, eJ, eI, True)
                    else:
                        categoryName = self.getCategoryNameFromTokens(sentenceGraph, tJ, tI, True)
                    examples.append( self.buildExample(tJ, tI, paths, sentenceGraph, categoryName, exampleIndex, eJ, eI) )
                    exampleIndex += 1
                else:
                    if "entities" in self.styles:
                        categoryName = self.getCategoryName(sentenceGraph, eI, eJ, False)
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
        # define features
        features = {}
        if True: #token1 != token2 and paths.has_key(token1) and paths[token1].has_key(token2):
            if token1 != token2 and paths.has_key(token1) and paths[token1].has_key(token2):
                path = paths[token1][token2]
            else:
                path = [token1, token2]
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
                    #self.multiEdgeFeatureBuilder.buildTerminusFeatures(path[0], edges[0][1]+edges[1][0], "t1", sentenceGraph) # remove for fast
                    #self.multiEdgeFeatureBuilder.buildTerminusFeatures(path[-1], edges[len(path)-1][len(path)-2]+edges[len(path)-2][len(path)-1], "t2", sentenceGraph) # remove for fast
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
            extra = {"xtype":"edge","type":"i","t1":path[0],"t2":path[-1]}
            extra["deprev"] = False
        else:
            extra = {"xtype":"edge","type":"i","t1":path[-1],"t2":path[0]}
            extra["deprev"] = True
        if entity1 != None:
            extra["e1"] = entity1
        if entity2 != None:
            extra["e2"] = entity2
        extra["categoryName"] = categoryName
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