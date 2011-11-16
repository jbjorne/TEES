from FeatureBuilder import FeatureBuilder
import numpy
#from numpy import *
import numpy.linalg
import networkx as NX
import copy
import sys
sys.path.append("../..")
import Core.ExampleUtils as ExampleUtils

def getHexColor(red, green, blue):
    """ convert an (R, G, B) tuple to #RRGGBB """
    hexcolor = '#%02x%02x%02x' % (int(red),int(green),int(blue))
    # that's it! '%02x' means zero-padded, 2-digit hex values
    return hexcolor

def getColorFromBRGSpectrum(value, minVal=0.0, maxVal=1.0):
    span = maxVal - minVal
    pos = value / span
    spanHalf = span / 2.0 
    blue = max((spanHalf - value)/spanHalf, 0.0) * 255
    red = max((spanHalf - abs(value-spanHalf))/spanHalf, 0.0) * 255
    green = max((value-spanHalf)/spanHalf, 0.0) * 255
    return getHexColor(red, green, blue)

def adjacencyMatrixToHtml(matrix, labels, filename):
    from HtmlBuilder import HtmlBuilder
    h = HtmlBuilder()
    h.newPage("test","")
    
    h.header("Adjacency Matrix", 3)
    h.table(1)
    rows, columns = matrix.shape
    h.tableRow() # title row
    h.tableData(None, True) # corner cell
    for i in range(columns):
        h.tableData(None, False)
        h.span( str(i), "font-size:smaller;font-weight:bold" )
        h.closeElement() # tableData
    h.closeElement() # title row
    
    for i in range(rows):
        h.tableRow()
        h.tableData(None, False)
        h.span( str(i), "font-size:smaller;font-weight:bold" )
        h.closeElement() # tableData
        for j in range(columns):            
            h.tableData(None, False)
            if matrix[i,j] != 0.0:
                style = "font-size:smaller;background-color:" + getColorFromBRGSpectrum(matrix[i,j]) #00FF00"
                h.span( str(matrix[i,j])[0:4], style )
            else:
                style = "font-size:smaller"
                h.span( "0", style )
            h.closeElement() # tableData
        h.closeElement() # tableRow
    
    h.closeElement() # table
    
    h.header("Legend", 4)
    h.table(1)
    h.tableRow()
    h.tableData(None, False)
    h.span( "0.0", "font-size:smaller" )
    h.closeElement() # tableData
    i = 0.1
    while i <= 1.0:
        h.tableData(None, False)
        h.span( str(i), "font-size:smaller;background-color:" + getColorFromBRGSpectrum(i) )
        h.closeElement() # tableData
        i += 0.1
    h.closeElement() # tableRow
    h.closeElement() # table
    
    if labels != None:
        h.header("Labels", 3)
        for i in range(len(labels)):
            string = str(i) + ": "
            first = True
            for label in labels[i]:
                if not first:
                    string += ", "
                string += label
                first = False
            h.span(string)
            h.lineBreak()
    
    h.write(filename)

class GraphKernelFeatureBuilder(FeatureBuilder):
    def __init__(self, featureSet):
        FeatureBuilder.__init__(self, featureSet)
    
    def buildGraphKernelFeatures(self, sentenceGraph, path):
        edgeList = []
        depGraph = sentenceGraph.dependencyGraph
        pt = path
        for i in range(1, len(path)):
            edgeList.extend(depGraph.getEdges(pt[i], pt[i-1]))
            edgeList.extend(depGraph.getEdges(pt[i-1], pt[i]))
        edges = edgeList
        adjacencyMatrix, labels = self._buildAdjacencyMatrix(sentenceGraph, path, edges)
        node_count = 2*len(sentenceGraph.tokens) + len(sentenceGraph.dependencies)
        
        if sentenceGraph.sentenceElement.attrib["id"] == "LLL.d0.s0":
            adjacencyMatrixToHtml(adjacencyMatrix, labels, "LLL.d0.s0_adjacency_matrix.html")
        
        allPathsMatrix = self._prepareMatrix(adjacencyMatrix, node_count)
        self._matrixToFeatures(allPathsMatrix, labels)
        if sentenceGraph.sentenceElement.attrib["id"] == "LLL.d0.s0":
            adjacencyMatrixToHtml(allPathsMatrix, labels, "LLL.d0.s0_all_paths_matrix.html")
            commentLines = []
            commentLines.extend(self.featureSet.toStrings())
            example = ["example_"+self.entity1.attrib["id"]+"_"+self.entity2.attrib["id"],"unknown",self.features]
            ExampleUtils.writeExamples([example],"LLL.d0.s0_example.txt",commentLines)
            #sys.exit("Debug files created")

    def _matrixToFeatures(self, W, labels):
        #proteins = set(["PROTEIN1", "PROTEIN2", "$$PROTEIN1", "$$PROTEIN2"]) 
        """Linearizes the representation of the graph"""
        linear = {}
        for i in range(W.shape[0]):
            for j in range(W.shape[1]):
                if W[i,j] > 0.00001: #i != j and W[i,j] > 0.3: #0.00001:
                    for label1 in labels[i]:
                        if (not "punct" in labels[i]) and (not "punct" in labels[j]):
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
        self._reduceWeightByDistance(sentenceGraph, weightByDependency)
        
        # Build dependency types
        allEdges = edges #self._getEdgeList(edges)
        
        #For each dependency
        depEdgePairs = []
        depGraphEdges = sentenceGraph.dependencyGraph.edges #()
        for dependency in sentenceGraph.dependencies:
            for edge in depGraphEdges:
                if edge[2] == dependency:
                    depEdgePairs.append( (dependency, edge) )
                    depGraphEdges.remove(edge)
            
        for depPair, index in zip(depEdgePairs, dep_indices):
            dep = depPair[1]
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
            if dep in allEdges:
                labels[index].add("sp_" + dep[2].attrib["type"])
            else:
                labels[index].add(dep[2].attrib["type"])
            
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
            # use the same approach as in MultiEdgeFeatureBuilder
            features = self.getTokenFeatures(node, sentenceGraph)
            if "txt_NAMED_ENT" in features:
                if self.entity1 in sentenceGraph.tokenIsEntityHead[node]:
                    features.remove("txt_NAMED_ENT")
                    features.append("txt_NAMED_ENT_1")
                elif self.entity2 in sentenceGraph.tokenIsEntityHead[node]:
                    features.remove("txt_NAMED_ENT")
                    features.append("txt_NAMED_ENT_2")
            if "noAnnType" in features:
                features.remove("noAnnType")
            
            # apply labels
            if node in path: # shortest path
                for feature in features:
                    labels[index].add("sp_"+feature)
                #labels[index].add("sp_"+self._getTokenText(path, sentenceGraph, node))
                #labels[index].add("sp_"+node.attrib["POS"])
            else:
                for feature in features:
                    labels[index].add(feature)
                #labels[index].add(self._getTokenText(path, sentenceGraph, node))
                #labels[index].add(node.attrib["POS"])
#            for code in node.metamapCodes:
#                labels[index].add(code)
#            if node.isPPIInteraction:
#                labels[index].add("1Nt3R4Ct")
            if preTagByToken.has_key(node):
                preTag = preTagByToken[node]
                for feature in features:
                    labels[index].add(preTag+feature)
                #labels[len(sentenceGraph.tokens)+index].add(preTag+self._getTokenText(path, sentenceGraph, node))
                #labels[len(sentenceGraph.tokens)+index].add(preTag+node.attrib["POS"])
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
        if edgeDict != None:
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
        allEdges = edges #self._getEdgeList(edges)
        
        for edge in allEdges:
            assert(weights.has_key(edge[2]))
            weights[edge[2]] = weight
                    
    def _reduceWeightByDistance(self, sentenceGraph, weights, zeroDistanceThreshold = 0.9, reduceFactor = 0.5):
        """ Reduces the weight of dependencies based on their distance
        from the nearest dependency whose weight is >= the threshold.
        """
        undirected = sentenceGraph.dependencyGraph.toUndirected() #.to_undirected()
        edges = undirected.edges
        tempGraph = NX.Graph(directed=False)
        for edge in edges:
            tempGraph.add_edge(edge[0], edge[1])
        tokenDistanceDict = NX.all_pairs_shortest_path_length(tempGraph, cutoff=999)
        dependencyDistances = {}

        zeroDistanceEdges = []
        for edge in edges:
            if weights[edge[2]] >= zeroDistanceThreshold:
                zeroDistanceEdges.append(edge)
                dependencyDistances[edge[2]] = 0
        
        # Cannot reduce weight if no node is over threshold
        if len(zeroDistanceEdges) == 0:
            return
        
        # Calculate distances
        for edge in edges:
            if edge in zeroDistanceEdges:
                continue
            shortestDistance = 99
            for zeroDistanceEdge in zeroDistanceEdges:
                if tokenDistanceDict.has_key(edge[0]):
                    if tokenDistanceDict[edge[0]].has_key(zeroDistanceEdge[0]):
                        if tokenDistanceDict[ edge[0] ][ zeroDistanceEdge[0] ] < shortestDistance:
                            shortestDistance = tokenDistanceDict[ edge[0] ][ zeroDistanceEdge[0] ]
                    if tokenDistanceDict[edge[0]].has_key(zeroDistanceEdge[1]):
                        if tokenDistanceDict[ edge[0] ][ zeroDistanceEdge[1] ] < shortestDistance:
                            shortestDistance = tokenDistanceDict[ edge[0] ][ zeroDistanceEdge[1] ]
                if tokenDistanceDict.has_key(edge[1]):
                    if tokenDistanceDict[edge[1]].has_key(zeroDistanceEdge[0]):
                        if tokenDistanceDict[ edge[1] ][ zeroDistanceEdge[0] ] < shortestDistance:
                            shortestDistance = tokenDistanceDict[ edge[1] ][ zeroDistanceEdge[0] ]
                    if tokenDistanceDict[edge[1]].has_key(zeroDistanceEdge[1]):
                        if tokenDistanceDict[ edge[1] ][ zeroDistanceEdge[1] ] < shortestDistance:
                            shortestDistance = tokenDistanceDict[ edge[1] ][ zeroDistanceEdge[1] ]
            #assert(not dependencyDistances.has_key(edge[2]))
            dependencyDistances[edge[2]] = shortestDistance + 1

        # Reduce weight
        for dependency in sentenceGraph.dependencies:
            if not dependencyDistances.has_key(dependency):
                dependencyDistances[dependency] = 99
            weights[dependency] *= pow(reduceFactor, max(dependencyDistances[dependency] - 1, 0))

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