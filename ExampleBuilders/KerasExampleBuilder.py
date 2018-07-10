import sys, os
thisPath = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(thisPath,"..")))
from ExampleBuilder import ExampleBuilder
from Core.IdSet import IdSet
import gzip, json
import Utils.Settings as Settings

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
        
        self.featureIds = self.featureSet
        self.labelIds = self.classSet
        
        self._setDefaultParameters(["directed", "undirected", "cutoff", "annotated_only", "all_positive", "wv", 
                                    "epochs", "html", "autoencode", "lr", "patience"])
        self.styles = self.getParameters(style)
        if self.styles["cutoff"]:
            self.styles["cutoff"] = int(self.styles["cutoff"])
        
        self.wvIndices = None
        self.embeddingMatrices = None
        if self.styles.get("wv") != None:
            indexPath = self.styles.get("wv") + "-indices.json.gz"
            if not os.path.exists(indexPath):
                indexPath = os.path.join(Settings.DATAPATH, "wv", indexPath)
            print >> sys.stderr, "Loading word vector indices from", indexPath
            with gzip.open(indexPath, "rt") as f:
                self.wvIndices = json.load(f)["indices"]
            self.embeddingMatrices = []
        
        self.dimMatrix = 32
        self.rangeMatrix = range(self.dimMatrix)
        self.featureMatrices = []
        self.labelMatrices = []
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
    
    def getEntityTypeFeatures(self, tokens, onlyGiven, negValue, sentenceGraph):
        features = []
        for token in tokens:
            if onlyGiven:
                entities = [x for x in sentenceGraph.tokenIsEntityHead[token] if x.get("given") == "True"]
            else:
                entities = [x for x in sentenceGraph.tokenIsEntityHead[token]]
            entFeatures = set()
            for entity in entities:
                entFeatures.add(entity.get("type"))
#                 for key in ("type", "mtmxNameShort"):
#                     if entity.get(key) != None:
#                         entFeatures.add(entity.get(key))
#                 if entity.get("mtmxSemTypes") != None:
#                     for semType in entity.get("mtmxSemTypes").split(","):
#                         entFeatures.add(semType)
            entFeatures = sorted(entFeatures)
            if len(entFeatures) == 0:
                features.append([("Eneg", negValue)])
            else:
                features.append([(x,1.0) for x in entFeatures])
        return features
    
    def buildSingleElementFeatures(self, pathTokens, sentenceGraph):
        depGraph = sentenceGraph.dependencyGraph
        pt = pathTokens
        # Edges directed relative to the path
        features = []
        for i in range(1,len(pathTokens)):
            for edge in depGraph.getEdges(pt[i], pt[i-1]):
                depType = edge[2].get("type")
                features.append(depType)# + ">")
            for edge in depGraph.getEdges(pt[i-1], pt[i]):
                depType = edge[2].get("type")
                features.append(depType)# + "<")
        return features
    
    def getEmbeddingIndex(self, token):
        tokText = token.get("text").lower()
        if tokText not in self.wvIndices:
            tokText = "[OoV]"
        return self.wvIndices[tokText]
    
    def buildExamplesFromGraph(self, sentenceGraph, outfile, goldGraph = None, structureAnalyzer=None):
        """
        Build examples for a single sentence. Returns a list of examples.
        See Core/ExampleUtils for example format.
        """
        
        # The annotated_only style skips sentences with no annotated interactions
        if self.styles.get("annotated_only") and len(sentenceGraph.interactions) == 0:
            return 1
        
        # The cutoff style limits example generation to the first n sentences
        if self.styles.get("cutoff") and len(self.featureMatrices) > self.styles.get("cutoff"):
            return 1
        
        # Whether to use directer or undirected interaction edges
        directed = self.getDirectionality(structureAnalyzer)
            
        # Filter entities, if needed
        sentenceGraph.mergeInteractionGraph(True)
        entities = sentenceGraph.mergedEntities
        self.exampleStats.addValue("Duplicate entities skipped", len(sentenceGraph.entities) - len(entities))
        
        # The dependency graph connects the tokens with the shortest paths
        depGraph = None
        if not self.styles.get("no_path"): #not self.hasStyle("no_path"):
            undirected = sentenceGraph.dependencyGraph.toUndirected()
            depGraph = undirected
            if self.styles.get("filter_shortest_path") != None: # For DDI use filter_shortest_path=conj_and
                depGraph.resetAnalyses() # just in case
                depGraph.FloydWarshall(self.filterEdge, {"edgeTypes":self.styles["filter_shortest_path"]})
        
        # Generate the two matrices in the format [row_index][column_index][feature_name]
        numTokens = len(sentenceGraph.tokens)
        featureMatrix = []
        labelMatrix = []
        embeddingMatrix = None
        if self.wvIndices != None:
            embeddingMatrix = []
        tokenList = [x.get("text") for x in sentenceGraph.tokens]
        negValue = 1 #0.000001 #0.001
        sourceEntityFeatures = self.getEntityTypeFeatures(sentenceGraph.tokens, True, negValue, sentenceGraph)
        targetEntityFeatures = self.getEntityTypeFeatures(sentenceGraph.tokens, False, negValue, sentenceGraph)
        for i in self.rangeMatrix:
            featureMatrix.append([])
            labelMatrix.append([])
            if embeddingMatrix != None:
                embeddingMatrix.append([])
            for j in self.rangeMatrix:
                features = {}
                labels = {}
                if embeddingMatrix != None:
                    embeddingFeatures = None
                if i >= numTokens or j >= numTokens: # Padding outside the sentence range (left empty, later fille with Numpy zeros)
                    #pass #features[self.featureSet.getId("padding")] = 1
                    self.setFeature(self.featureIds, features, "[out]", negValue)
                    self.setFeature(self.labelIds, labels, "[out]", negValue)
                    if embeddingMatrix != None:
                        embeddingFeatures = {"0":self.wvIndices["[out]"], "1":self.wvIndices["[out]"]}
                elif i == j: # The diagonal defines the linear order of the tokens in the sentence
                    token = sentenceGraph.tokens[i]
                    #self.setFeature(self.sourceIds, sourceFeatures, "E")
                    self.setFeature(self.featureIds, features, token.get("POS"))
                    if embeddingMatrix != None:
                        embeddingFeatures = {"0":self.getEmbeddingIndex(token), "1":self.getEmbeddingIndex(token)}
#                     sourceEntityTypes = []
#                     targeEntityTypes = []
#                     if len(sentenceGraph.tokenIsEntityHead[token]) > 0: # The token is the head token of an entity
#                         sourceEntityTypes = [x.get("type") for x in sentenceGraph.tokenIsEntityHead[token] if x.get("given") == "True"]
#                         targeEntityTypes = [x.get("type") for x in sentenceGraph.tokenIsEntityHead[token]]
#                     if len(sourceEntityTypes) == 0: # There is no entity for this token
#                         sourceEntityTypes = ["neg"]
#                     if len(targeEntityTypes) == 0: # There is no entity for this token
#                         targeEntityTypes = ["neg"]
                    for eType, eValue in sourceEntityFeatures[i]:
                        self.setFeature(self.featureIds, features, eType, eValue)
                    for eType, eValue in targetEntityFeatures[i]:
                        self.setFeature(self.labelIds, labels, eType, eValue)
                else: # This element of the adjacency matrix describes the relation from token i to token j
                    # Define the dependency features for the source matrix
                    tI = sentenceGraph.tokens[i]
                    tJ = sentenceGraph.tokens[j]
                    if embeddingMatrix != None:
                        embeddingFeatures = {"0":self.getEmbeddingIndex(tI), "1":self.getEmbeddingIndex(tJ)}
                    for eType, eValue in sourceEntityFeatures[i]:
                        self.setFeature(self.featureIds, features, "A:" + eType, eValue)
                    for eType, eValue in sourceEntityFeatures[j]:
                        self.setFeature(self.featureIds, features, "B:" + eType, eValue)
                    shortestPaths = depGraph.getPaths(tI, tJ)
                    depTypes = set()
                    if len(shortestPaths) > 0: # There is a path of dependencies between these two tokens
                        #path = shortestPaths[0]
                        for path in shortestPaths:
                            for edgeFeature in self.buildSingleElementFeatures(path, sentenceGraph):
                                self.setFeature(self.featureIds, features, edgeFeature)
#                         if True: #len(path) == 2:
#                             #for tokenIndex in (0, -1): # The first and last token in the path
#                             #    self.setFeature(self.sourceIds, sourceFeatures, "T" + str(tokenIndex) + ":" + path[tokenIndex].get("POS"))
#                             for k in range(1, len(path)): # A bag of dependencies for this shortest path
#                                 for edge in depGraph.getEdges(path[k], path[k-1]): # + depGraph.getEdges(path[k-1], path[k]):
#                                     if edge[0] == path[k]:
#                                         eDir = ">"
#                                     else:
#                                         eDir = "<"
#                                     depTypes.add(eDir + edge[2].get("type")) #self.setFeature(self.sourceIds, sourceFeatures, edge[2].get("type"))
#                                     #if k == 1:
#                                     #    self.setFeature(self.sourceIds, sourceFeatures, "a:" + eDir + edge[2].get("type"))
#                                     #if k == len(path) - 1:
#                                     #    self.setFeature(self.sourceIds, sourceFeatures, "b:" + eDir + edge[2].get("type"))
                    if len(depTypes) == 0:
                        depTypes.add("DNeg")
                    for depType in sorted(depTypes):
                        self.setFeature(self.featureIds, features, depType)
                    #else:
                    #    self.setFeature(self.sourceIds, sourceFeatures, "D:0") # no path
                    # Define the relation features (labels) for the target matrix
                    if self.styles.get("all_positive"): # Add a target relation for each pair of entities
                        #if len(targetEntityFeatures[i]) > 0 and len(targetEntityFeatures[j]) > 0:
                        if (targetEntityFeatures[i][0][0] != "Eneg") and (targetEntityFeatures[j][0][0] != "Eneg"):
                            self.setFeature(self.labelIds, labels, "REL")
                        #else:
                        #    self.setFeature(self.targetIds, targetFeatures, "neg", negValue)
                    else:
                        intTypes = set()
                        intEdges = sentenceGraph.interactionGraph.getEdges(tI, tJ)
                        if not directed:
                            intEdges = intEdges + sentenceGraph.interactionGraph.getEdges(tJ, tI)
                        for intEdge in intEdges:
                            intTypes.add(intEdge[2].get("type"))
                        if len(intTypes) > 0: # A bag of interactions for all interaction types between the two tokens
                            for intType in sorted(list(intTypes)):
                                self.setFeature(self.labelIds, labels, intType)
                        else:
                            self.setFeature(self.labelIds, labels, "Ineg", negValue)
                    # Define the features for the two entities
#                     for eType, eValue in sourceEntityFeatures[i]:
#                         self.setFeature(self.sourceIds, sourceFeatures, eType + "[0]", eValue)
#                     for eType, eValue in sourceEntityFeatures[j]:
#                         self.setFeature(self.sourceIds, sourceFeatures, eType + "[1]", eValue)
                featureMatrix[-1].append(features)
                labelMatrix[-1].append(labels)
                if embeddingMatrix != None:
                    assert len(embeddingFeatures) == 2
                    embeddingMatrix[-1].append(embeddingFeatures)
        
        # Add this sentences's matrices and list of tokens to the result lists
        self.featureMatrices.append(featureMatrix)
        self.labelMatrices.append(labelMatrix)
        if embeddingMatrix != None:
            self.embeddingMatrices.append(embeddingMatrix)
        self.tokenLists.append(tokenList)
        return 1 # One sentence is one example