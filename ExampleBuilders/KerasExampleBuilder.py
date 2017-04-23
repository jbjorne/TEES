import sys, os
thisPath = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(thisPath,"..")))
from ExampleBuilder import ExampleBuilder
from Core.IdSet import IdSet

class KerasExampleBuilder(ExampleBuilder):
    """
    Adjacency matrix generation. This ExampleBuilder generates one source and one target
    adjacency matrix per sentence. The generated matrices are stored in the self.sourceMatrices
    and self.targetMatrices variables of the KerasExampleBuilder object. 
    
    Of the two IdSets, featureSet is used for source features and classSet for target features 
    (labels). Unlike with other TEES ExampleBuilders, the feature keys in the produced matrices
    are feature names, not feature ids.
    """
    def __init__(self, style=None, classSet=None, featureSet=None, gazetteerFileName=None, skiplist=None):
        if classSet == None:
            classSet = IdSet(0)
        if featureSet == None:
            featureSet = IdSet(0)
        
        ExampleBuilder.__init__(self, classSet, featureSet)
        
        self.sourceIds = self.featureSet
        self.targetIds = self.classSet
        
        self._setDefaultParameters(["directed", "undirected", "cutoff", "annotated_only", "epochs"])
        self.styles = self.getParameters(style)
        if self.styles["cutoff"]:
            self.styles["cutoff"] = int(self.styles["cutoff"])
        
        self.dimMatrix = 50
        self.rangeMatrix = range(self.dimMatrix)
        self.sourceMatrices = []
        self.targetMatrices = []
        self.tokenLists = []
    
    def setFeature(self, featureSet, features, name, value=1):
        featureSet.getId(name)
        features[name] = value
    
    def getDirectionality(self, structureAnalyzer):
        if self.styles["directed"] == None and self.styles["undirected"] == None: # determine directedness from corpus
            return structureAnalyzer.hasDirectedTargets()
        elif self.styles["directed"]:
            assert self.styles["undirected"] in [None, False]
            return True
        elif self.styles["undirected"]:
            assert self.styles["directed"] in [None, False]
            return False
    
    def buildExamplesFromGraph(self, sentenceGraph, outfile, goldGraph = None, structureAnalyzer=None):
        """
        Build examples for a single sentence. Returns a list of examples.
        See Core/ExampleUtils for example format.
        """
        
        # The annotated_only style skips sentences with no annotated interactions
        if self.styles.get("annotated_only") and len(sentenceGraph.interactions) == 0:
            return 1
        
        # The cutoff style limits example generation to the first n sentences
        if self.styles.get("cutoff") and len(self.sourceMatrices) > self.styles.get("cutoff"):
            return 1
        
        # Whether to use directer or undirected interaction edges
        directed = self.getDirectionality(structureAnalyzer)
            
        # Filter entities, if needed
        sentenceGraph.mergeInteractionGraph(True)
        entities = sentenceGraph.mergedEntities
        self.exampleStats.addValue("Duplicate entities skipped", len(sentenceGraph.entities) - len(entities))
        
        # The dependency graph connects the tokens with the shortest paths
        depGraph = None
        if not self.hasStyle("no_path"):
            undirected = sentenceGraph.dependencyGraph.toUndirected()
            depGraph = undirected
            if self.styles.get("filter_shortest_path") != None: # For DDI use filter_shortest_path=conj_and
                depGraph.resetAnalyses() # just in case
                depGraph.FloydWarshall(self.filterEdge, {"edgeTypes":self.styles["filter_shortest_path"]})
        
        # Generate the two matrices in the format [row_index][column_index][feature_name]
        numTokens = len(sentenceGraph.tokens)
        sourceMatrix = []
        targetMatrix = []
        tokenList = [x.get("text") for x in sentenceGraph.tokens]
        for i in self.rangeMatrix:
            sourceMatrix.append([])
            targetMatrix.append([])
            for j in self.rangeMatrix:
                sourceFeatures = {}
                targetFeatures = {}
                if i >= numTokens or j >= numTokens: # Padding outside the sentence range (left empty, later fille with Numpy zeros)
                    pass #features[self.featureSet.getId("padding")] = 1
                elif i == j: # The diagonal defines the linear order of the tokens in the sentence
                    token = sentenceGraph.tokens[i]
                    self.setFeature(self.sourceIds, sourceFeatures, token.get("POS"))
                    if len(sentenceGraph.tokenIsEntityHead[token]) > 0: # The token is the head token of an entity
                        for entity in sentenceGraph.tokenIsEntityHead[token]:
                            if entity.get("given") == "True": # This entity can be used as a training feature
                                self.setFeature(self.sourceIds, sourceFeatures, entity.get("type"))
                            self.setFeature(self.targetIds, targetFeatures, entity.get("type"))
                    else: # There is no entity for this token
                        self.setFeature(self.sourceIds, sourceFeatures, "E:0")
                else: # This element of the adjacency matrix describes the relation from token i to token j
                    # Define the dependency features for the source matrix
                    tI = sentenceGraph.tokens[i]
                    tJ = sentenceGraph.tokens[j]
                    shortestPaths = depGraph.getPaths(tI, tJ)
                    if len(shortestPaths) > 0: # There is a path of dependencies between these two tokens
                        path = shortestPaths[0]
                        for tokenIndex in (0, -1): # The first and last token in the path
                            self.setFeature(self.sourceIds, sourceFeatures, "T" + str(tokenIndex) + ":" + path[tokenIndex].get("POS"))
                        for k in range(1, len(path)): # A bag of dependencies for this shortest path
                            for edge in depGraph.getEdges(path[k], path[k-1]) + depGraph.getEdges(path[k-1], path[k]):
                                self.setFeature(self.sourceIds, sourceFeatures, edge[2].get("type"))
                    else:
                        self.setFeature(self.sourceIds, sourceFeatures, "D:0") # no path
                    # Define the relation features (labels) for the target matrix
                    intTypes = set()
                    intEdges = sentenceGraph.interactionGraph.getEdges(tI, tJ)
                    if not directed:
                        intEdges = intEdges + sentenceGraph.interactionGraph.getEdges(tJ, tI)
                    for intEdge in intEdges:
                        intTypes.add(intEdge[2].get("type"))
                    if len(intTypes) > 0: # A bag of interactions for all interaction types between the two tokens
                        for intType in sorted(list(intTypes)):
                            self.setFeature(self.targetIds, targetFeatures, intType)
                sourceMatrix[-1].append(sourceFeatures)
                targetMatrix[-1].append(targetFeatures)
        
        # Add this sentences's matrices and list of tokens to the result lists
        self.sourceMatrices.append(sourceMatrix)
        self.targetMatrices.append(targetMatrix)
        self.tokenLists.append(tokenList)
        return 1 # One sentence is one example