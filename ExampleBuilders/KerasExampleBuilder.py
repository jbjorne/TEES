import sys, os
thisPath = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(thisPath,"..")))
from ExampleBuilder import ExampleBuilder
from Core.IdSet import IdSet
import numpy as np
import gzip
import json

class KerasExampleBuilder(ExampleBuilder):
    def __init__(self, style=None, classSet=None, featureSet=None, gazetteerFileName=None, skiplist=None):
        if classSet == None:
            classSet = IdSet(1)
        if featureSet == None:
            featureSet = IdSet()
        
        ExampleBuilder.__init__(self, classSet, featureSet)
        
        self.dimMatrix = 30
        self.rangeMatrix = range(self.dimMatrix)
        self.sourceMatrices = []
        self.targetMatrices = []
        self.stringKeys = True
    
    #def processSentence(self, sentence, outfile, goldSentence=None, structureAnalyzer=None):
        #return ExampleBuilder.processSentence(self, sentence, outfile, goldSentence=goldSentence, structureAnalyzer=structureAnalyzer)
    
    def saveMatrices(self, filePath):
        assert self.sourceMatrices != None and self.targetMatrices != None
        with gzip.open(filePath, "wt") as f:
            json.dump({"source":self.sourceMatrices, "target":self.targetMatrices}, f)
    
    def loadMatrices(self, filePath):
        with gzip.open(filePath, "rt") as f:
            data = json.load(f)
            self.sourceMatrices = data["source"]
            self.targetMatrices = data["target"]
    
    def setFeature(self, features, name, value=1):
        featureId = self.featureSet.getId(name)
        if self.stringKeys:
            features[name] = value
        else:
            features[featureId] = value
    
    def buildExamplesFromGraph(self, sentenceGraph, outfile, goldGraph = None, structureAnalyzer=None):
        """
        Build examples for a single sentence. Returns a list of examples.
        See Core/ExampleUtils for example format.
        """
#         #examples = []
#         exampleIndex = 0
#         # example directionality
#         if self.styles["directed"] == None and self.styles["undirected"] == None: # determine directedness from corpus
#             examplesAreDirected = structureAnalyzer.hasDirectedTargets()
#         elif self.styles["directed"]:
#             assert self.styles["undirected"] in [None, False]
#             examplesAreDirected = True
#         elif self.styles["undirected"]:
#             assert self.styles["directed"] in [None, False]
#             examplesAreDirected = False
    
            
        # Filter entities, if needed
        sentenceGraph.mergeInteractionGraph(True)
        entities = sentenceGraph.mergedEntities
        self.exampleStats.addValue("Duplicate entities skipped", len(sentenceGraph.entities) - len(entities))
        
#         # Connect to optional gold graph
#         entityToGold = None
#         if goldGraph != None:
#             entityToGold = EvaluateInteractionXML.mapEntities(entities, goldGraph.entities)
        
        depGraph = None
        if not self.styles["no_path"]:
            undirected = sentenceGraph.dependencyGraph.toUndirected()
            depGraph = undirected
            if self.styles["filter_shortest_path"] != None: # For DDI use filter_shortest_path=conj_and
                depGraph.resetAnalyses() # just in case
                depGraph.FloydWarshall(self.filterEdge, {"edgeTypes":self.styles["filter_shortest_path"]})
        
        # Generate examples based on interactions between entities or interactions between tokens
        numTokens = len(sentenceGraph.tokens)
        sourceMatrix = []
        targetMatrix = []
        for i in self.rangeMatrix:
            sourceMatrix.append([])
            targetMatrix.append([])
            for j in self.rangeMatrix:
                sourceFeatures = {}
                targetFeatures = {}
                if i >= numTokens or j >= numTokens:
                    pass #features[self.featureSet.getId("padding")] = 1
                elif i == j: # diagonal
                    self.setFeature(sourceFeatures, "path-zero")
                    token = sentenceGraph.tokens[i]
                    self.setFeature(sourceFeatures, token.get("POS"))
                    if len(self.tokenIsEntityHead[token]) > 0:
                        self.setFeature(sourceFeatures, "entity")
                        self.setFeature(targetFeatures, "entity")
                        for entity in self.tokenIsEntityHead[token]:
                            self.setFeature(sourceFeatures, entity.get("type"))
                            self.setFeature(targetFeatures, entity.get("type"))
                else:
                    # define features
                    tI = sentenceGraph.tokens[i]
                    tJ = sentenceGraph.tokens[j]
                    shortestPaths = depGraph.getPaths(tI, tJ)
                    if len(shortestPaths) > 0:
                        path = shortestPaths[0]
                        self.setFeature(sourceFeatures, "P:T") # path true
                        self.setFeature(sourceFeatures, "P:L", len(path)) # path length
                        for token in path:
                            self.setFeature(sourceFeatures, token.get("POS"))
                        for i in range(1, len(path)):
                            for edge in depGraph.getEdges(path[i], path[i-1]), depGraph.getEdges(path[i-1], path[i]):
                                self.setFeature(sourceFeatures, edge.get("type"))
                    else:
                        self.setFeature(sourceFeatures, "P:F") # path false
                sourceMatrix[-1].append(sourceFeatures)
                targetMatrix[-1].append(targetFeatures)
        
        self.sourceMatrices.append(sourceMatrix)
        self.targetMatrices.append(targetMatrix)