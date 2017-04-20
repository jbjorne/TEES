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
        self.tokenLists = []
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
        features[self.featureSet.getId(name)] = value
        #featureId = self.featureSet.getId(name)
        #if self.stringKeys:
        #    features[name] = value
        #else:
        #    features[featureId] = value
    
    def buildExamplesFromGraph(self, sentenceGraph, outfile, goldGraph = None, structureAnalyzer=None):
        """
        Build examples for a single sentence. Returns a list of examples.
        See Core/ExampleUtils for example format.
        """
        if self.exampleCount > 0:
            return
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
        if not self.hasStyle("no_path"):
            undirected = sentenceGraph.dependencyGraph.toUndirected()
            depGraph = undirected
            if self.styles.get("filter_shortest_path") != None: # For DDI use filter_shortest_path=conj_and
                depGraph.resetAnalyses() # just in case
                depGraph.FloydWarshall(self.filterEdge, {"edgeTypes":self.styles["filter_shortest_path"]})
        
        # Generate examples based on interactions between entities or interactions between tokens
        numTokens = len(sentenceGraph.tokens)
        sourceMatrix = []
        targetMatrix = []
        tokenList = [x for x in sentenceGraph.tokens]
        for i in self.rangeMatrix:
            sourceMatrix.append([])
            targetMatrix.append([])
            for j in self.rangeMatrix:
                sourceFeatures = {}
                targetFeatures = {}
                if i >= numTokens or j >= numTokens:
                    pass #features[self.featureSet.getId("padding")] = 1
                elif i == j: # diagonal
                    #self.setFeature(sourceFeatures, "P:0")
                    token = sentenceGraph.tokens[i]
                    self.setFeature(sourceFeatures, token.get("POS"))
                    if len(sentenceGraph.tokenIsEntityHead[token]) > 0:
                        #self.setFeature(sourceFeatures, "E:1")
                        #self.setFeature(targetFeatures, "E:1")
                        for entity in sentenceGraph.tokenIsEntityHead[token]:
                            self.setFeature(sourceFeatures, entity.get("type"))
                            self.setFeature(targetFeatures, entity.get("type"))
                    else:
                        self.setFeature(sourceFeatures, "E:0")
                        self.setFeature(targetFeatures, "E:0")
                else:
                    # define features
                    tI = sentenceGraph.tokens[i]
                    tJ = sentenceGraph.tokens[j]
                    shortestPaths = depGraph.getPaths(tI, tJ)
                    if len(shortestPaths) > 0:
                        path = shortestPaths[0]
                        if len(path) > 2:
                            self.setFeature(sourceFeatures, "D:0") # path > 2
                        else:
                            #self.setFeature(sourceFeatures, "P:T") # path true
                            #self.setFeature(sourceFeatures, "P:L", len(path)) # path length
                            for tokenIndex in range(len(path)):
                                self.setFeature(sourceFeatures, "T" + str(tokenIndex) + ":" + path[tokenIndex].get("POS"))
                            for k in range(1, len(path)):
                                for edge in depGraph.getEdges(path[k], path[k-1]) + depGraph.getEdges(path[k-1], path[k]):
                                    self.setFeature(sourceFeatures, edge[2].get("type"))
                    else:
                        self.setFeature(sourceFeatures, "D:0") # no path
                sourceMatrix[-1].append(sourceFeatures)
                targetMatrix[-1].append(targetFeatures)
        
        self.sourceMatrices.append(sourceMatrix)
        self.targetMatrices.append(targetMatrix)
        self.tokenLists.append(tokenList)
        return 1