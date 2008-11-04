from FeatureBuilder import FeatureBuilder
import numpy
#from numpy import *
import numpy.linalg
import copy

class GraphKernelFeatureBuilder(FeatureBuilder):
    def __init__(self, featureSet):
        FeatureBuilder.__init__(self, featureSet)
    
    def buildGraphKernelFeatures(self, sentenceGraph, path, edges):
        adjacencyMatrix, labels = self._buildAdjacencyMatrix(sentenceGraph, path, edges)
        node_count = 2*len(sentenceGraph.tokens) + len(sentenceGraph.dependencies)
        allPathsMatrix = self._prepareMatrix(adjacencyMatrix, node_count)
        self._matrixToFeatures(allPathsMatrix, labels)

    def _matrixToFeatures(self, W, labels):
        #proteins = set(["PROTEIN1", "PROTEIN2", "$$PROTEIN1", "$$PROTEIN2"]) 
        """Linearizes the representation of the graph"""
        linear = {}
        for i in range(W.shape[0]):
            for j in range(W.shape[1]):
                if W[i,j] > 0.00001:
                    for label1 in labels[i]:
                        for label2 in labels[j]:
                            #if label1 in proteins or label2 in proteins:
                            label = label1+"_$_"+label2
                            self.features[self.featureSet.getId(label)] = W[i,j]

    def _prepareMatrix(self, adjacencyMatrix, node_count, dtyp=numpy.float64):
        W = adjacencyMatrix * -1.0
#        W = adjacencyMatrix
#        for i in range(adjacencyMatrix.shape[0]):
#            for j in range(adjacencyMatrix.shape[1]):
#                adjacencyMatrix[i,j] *= -1.0
        W += numpy.mat(numpy.identity(node_count, dtype = dtyp))    
        return numpy.linalg.inv(W) - numpy.mat(numpy.identity(node_count, dtype=dtyp))    
    
    def _getTokenId(self, tokenElement):
        """ Returns the position id of the token """
        return int(tokenElement.attrib["id"].split("_")[1])
    
    def _getTokenText(self, path, sentenceGraph, token):
        tokenText = sentenceGraph.getTokenText(token)
        if tokenText == "NAMED_ENT":
            if token == path[0]:
                tokenText = "NAMED_ENT_1"
            elif token == path[-1]:
                tokenText = "NAMED_ENT_2"
        return tokenText

    def _buildAdjacencyMatrix(self, sentenceGraph, path, edges, floattype=numpy.float64, directed=True, linearOrderWeight=0.9):
        """ Returns a Numpy-matrix
        """
        #For each token, 2 nodes are allocated. For each dependency, one node is allocated
        node_count = 2*len(sentenceGraph.tokens) + len(sentenceGraph.dependencies)
        # Make the adjacency matrix of the graph
        adjMatrix = numpy.mat(numpy.zeros((node_count,node_count), dtype = floattype))
        #A dictionary of labels is associated with each node
        labels = [set([]) for x in range(node_count)]
        #The word nodes have indices 0..2*len(tokens), the dependency nodes have the rest of the indices.
        dep_indices = range(2*len(sentenceGraph.tokens), node_count)
        
        # Calculate dependency weights
        weightByDependency = {}
        self._setAllDependencyWeights(sentenceGraph, weightByDependency, 0.3)
        self._setDependencyWeightsByPath(edges, weightByDependency, 0.9)
        
        # Build dependency types
        allEdges = self._getEdgeList(edges)
        
        #For each dependency
        for dep, index in zip(sentenceGraph.dependencyGraph.edges(), dep_indices):
            #Token1-dependency, and dependency-token2 weights are added        
            adjMatrix[self._getTokenId(dep[0])-1, index] = weightByDependency[dep[2]]
            adjMatrix[index, self._getTokenId(dep[1])-1] = weightByDependency[dep[2]]
            #For undirected graphs, the links would also go the other way
            if not directed:
                adjMatrix[self._getTokenId(dep[1])-1, index] = weightByDependency[dep[2]]
                adjMatrix[index, self._getTokenId(dep[0])-1] = weightByDependency[dep[2]]
           
#            if type(dep.ppiType) == types.ListType:
#                for i in dep.ppiType:
#                    labels[index].add(i)
#            else:
#                labels[index].add(dep.ppiType)
            labels[index].add(dep[2].attrib["type"])
            if dep in allEdges:
                labels[index].add("sp_" + dep[2].attrib["type"])
            
        #Add the linear order of the sentence to the matrix
        for i in range(len(sentenceGraph.tokens),2*len(sentenceGraph.tokens)-1):
            adjMatrix[i,i+1] = linearOrderWeight
            if not directed:
                adjMatrix[i+1,i] = linearOrderWeight
    
        #For each token
        #preTagByToken = self._addPositionTags(sentenceGraph, sentenceGraph.entitiesByToken[path[0]], sentenceGraph.entitiesByToken[path[-1]])
        preTagByToken = self._addPositionTags(sentenceGraph, [path[0]], [path[-1]])
        for node in sentenceGraph.tokens:
            index = self._getTokenId(node) - 1
            if node in path: # shortest path
                labels[index].add("sp_"+self._getTokenText(path, sentenceGraph, node))
                labels[index].add("sp_"+node.attrib["POS"])
            else:
                labels[index].add(self._getTokenText(path, sentenceGraph, node))
                labels[index].add(node.attrib["POS"])
#            for code in node.metamapCodes:
#                labels[index].add(code)
#            if node.isPPIInteraction:
#                labels[index].add("1Nt3R4Ct")
            if preTagByToken.has_key(node):
                preTag = preTagByToken[node]
                labels[len(sentenceGraph.tokens)+index].add(preTag+self._getTokenText(path, sentenceGraph, node))
                labels[len(sentenceGraph.tokens)+index].add(preTag+node.attrib["POS"])
#                for code in node.metamapCodes:
#                    labels[len(tokensById)+index].add(preTag+code)
#                if node.isPPIInteraction:
#                    labels[len(tokensById)+index].add(preTag+"1Nt3R4Ct")
        
        return adjMatrix, labels

    def _setAllDependencyWeights(self, sentenceGraph, weights, weight):
        """ All weights are set to the given value
        """
        for node in sentenceGraph.dependencies:
            weights[node] = weight
    
    def _getEdgeList(self, edgeDict):
        allEdges = []
        keys1 = edgeDict.keys()
        keys1.sort()
        for k1 in keys1:
            keys2 = edgeDict[k1].keys()
            keys2.sort()
            for k2 in keys2:
                allEdges.extend(edgeDict[k1][k2])
        return allEdges
    
    def _setDependencyWeightsByPath(self, edges, weights, weight):
        """ The weights of all dependencies in specified paths are set to the
        given value
        """
        allEdges = self._getEdgeList(edges)
        
        for edge in allEdges:
            assert(weights.has_key(edge[2]))
            weights[edge[2]] = weight
                    
#    def reduceWeightByDistance(self, zeroDistanceThreshold = 0.9, reduceFactor = 0.5):
#        """ Reduces the weight of dependencies based on their distance
#        from the nearest dependency whose weight is >= the threshold.
#        """
#        zeroDistanceDependencies = []
#        # Initialize distances to a large number
#        for node in self.dependenciesById.values():
#            node.weightDistance = 99999999
#            if node.ppiWeight >= zeroDistanceThreshold:
#                node.weightDistance = 0
#                zeroDistanceDependencies.append(node)
#            for i in node.fro.dependencies:
#                assert(i in self.dependenciesById.values())
#            for i in node.to.dependencies:
#                assert(i in self.dependenciesById.values())
#        
#        # Cannot reduce weight if no node is over threshold
#        if len(zeroDistanceDependencies) == 0:
#            return
#        
#        # Calculate distances
#        for node in zeroDistanceDependencies:
#            node.setDistance(0)
#        
#        # Reduce weight
#        for node in self.dependenciesById.values():
#            node.ppiWeight *= pow(reduceFactor, max(node.weightDistance - 1, 0))

#    def setPPIPrefixForDependencies(self, sentenceGraph, weightByDependency, prefix, threshold):
#        """ Sets the dependencies ppiType to their dependencyType, 
#        and adds a prefix if their weight is over a given threshold 
#        """
#        for dependency in sentenceGraph.dependencies:
#            if weightByDependency[dependency] >= threshold:
#                dependency.to.isOnShortestPath = True
#                dependency.fro.isOnShortestPath = True
#                if type(dependency.dependencyType) == types.ListType:
#                    dependency.ppiType = []
#                    for i in range(len(dependency.dependencyType)):
#                        dependency.ppiType.append(prefix + dependency.dependencyType[i])
#                else:
#                    dependency.ppiType = prefix + dependency.dependencyType
#            else:
#                if type(dependency.dependencyType) == types.ListType:
#                    dependency.ppiType = []
#                    for i in range(len(dependency.dependencyType)):
#                        dependency.ppiType.append(dependency.dependencyType[i])
#                else:
#                    dependency.ppiType = dependency.dependencyType
    
    def _addPositionTags(self, sentenceGraph, entity1Tokens, entity2Tokens):
        """ Sets a prefix to the tokens ppiText based on their linear
        order in the sentence.
        """
        entity1TokenIds = []
        for token in entity1Tokens:
            entity1TokenIds.append(self._getTokenId(token))
        entity2TokenIds = []
        for token in entity2Tokens:
            entity2TokenIds.append(self._getTokenId(token))
        entity1FirstTokenId = min(entity1TokenIds)
        entity2LastTokenId = max(entity2TokenIds)
        
        preTagByToken = {}
        for token in sentenceGraph.tokens:
            pretag = "$$"
            tokenId = self._getTokenId(token)
            if not (tokenId in entity1TokenIds or tokenId in entity2TokenIds):
                if tokenId < entity1FirstTokenId:
                    pretag = "$B$"
                elif tokenId > entity2LastTokenId:
                    pretag = "$A$"
            preTagByToken[token] = pretag
        
        return preTagByToken