import sys
sys.path.append("..")
from Core.ExampleBuilder import ExampleBuilder
from Core.IdSet import IdSet
from FeatureBuilders.MultiEdgeFeatureBuilder import MultiEdgeFeatureBuilder
import networkx as NX

class MultiEdgeExampleBuilder(ExampleBuilder):
    def __init__(self, style=["typed","headsOnly"], length=[1,2,3], types=[]):
        ExampleBuilder.__init__(self)
        self.classSet = IdSet(1)
        assert( self.classSet.getId("neg") == 1 )
        self.multiEdgeFeatureBuilder = MultiEdgeFeatureBuilder(self.featureSet)
        self.styles = style
        self.pathLengths = length
        self.types = types
    
    def filterEdgesByType(self, edges, typesToInclude):
        if len(typesToInclude) == 0:
            return edges
        edgesToKeep = []
        for edge in edges:
            if edge.attrib["type"] in typesToInclude:
                edgesToKeep.append(edge)
        return edgesToKeep
     
    def buildExamples(self, sentenceGraph):
        examples = []
        exampleIndex = 0
        
        undirected = sentenceGraph.dependencyGraph.to_undirected()
        #undirected = self.makeUndirected(sentenceGraph.dependencyGraph)
        paths = NX.all_pairs_shortest_path(undirected, cutoff=4)
        for i in range(len(sentenceGraph.tokens)-1):
            for j in range(i+1,len(sentenceGraph.tokens)):
                tI = sentenceGraph.tokens[i]
                tJ = sentenceGraph.tokens[j]
                # only consider paths between entities (NOTE! entities, not only named entities)
                if "headsOnly" in self.styles:
                    if (sentenceGraph.tokenIsEntityHead[tI] == None) or (sentenceGraph.tokenIsEntityHead[tJ] == None):
                        continue

                # define class
                positive = False
                if sentenceGraph.interactionGraph.has_edge(tI, tJ):
                    intEdges = sentenceGraph.interactionGraph.get_edge(tI, tJ)
                    intEdges = self.filterEdgesByType(intEdges, self.types)
                    for intEdge in intEdges:
                        categoryName = intEdge.attrib["type"]                      
                        self.buildExample(tI, tJ, paths, sentenceGraph, categoryName, examples, exampleIndex)
                        exampleIndex += 1
                        positive = True
                if not positive:
                    self.buildExample(tI, tJ, paths, sentenceGraph, "neg", examples, exampleIndex)
                    exampleIndex += 1
                
                positive = False
                if sentenceGraph.interactionGraph.has_edge(tJ, tI):
                    intEdges = sentenceGraph.interactionGraph.get_edge(tJ, tI)
                    intEdges = self.filterEdgesByType(intEdges, self.types)
                    for intEdge in intEdges:
                        categoryName = intEdge.attrib["type"]
                        self.buildExample(tJ, tI, paths, sentenceGraph, categoryName, examples, exampleIndex)
                        exampleIndex += 1
                        positive = True
                if not positive:
                    self.buildExample(tJ, tI, paths, sentenceGraph, "neg", examples, exampleIndex)
                    exampleIndex += 1

        return examples
    
    def buildExample(self, token1, token2, paths, sentenceGraph, categoryName, examples, exampleIndex):
        # define features
        features = {}
        if paths.has_key(token1) and paths[token1].has_key(token2):
            path = paths[token1][token2]
            if len(self.pathLengths) != 0 and len(path)-1 in self.pathLengths:
                edges = self.multiEdgeFeatureBuilder.getEdges(sentenceGraph.dependencyGraph, path)
                self.multiEdgeFeatureBuilder.setFeatureVector(features)
                self.multiEdgeFeatureBuilder.buildPathLengthFeatures(path)
                self.multiEdgeFeatureBuilder.buildTerminusTokenFeatures(path, sentenceGraph)
                self.multiEdgeFeatureBuilder.buildSingleElementFeatures(path, edges, sentenceGraph)
                self.multiEdgeFeatureBuilder.buildPathGrams(2, path, edges, sentenceGraph)
                self.multiEdgeFeatureBuilder.buildPathGrams(3, path, edges, sentenceGraph)
                #self.buildEdgeCombinations(path, edges, sentenceGraph, features)
                #self.buildTerminusFeatures(path[0], "t1", sentenceGraph, features)
                #self.buildTerminusFeatures(path[-1], "t2", sentenceGraph, features)
                self.multiEdgeFeatureBuilder.buildPathEdgeFeatures(path, edges, sentenceGraph)
                self.multiEdgeFeatureBuilder.setFeatureVector(None)
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
        # make example
        if "binary" in self.styles:
            if categoryName != "neg":
                category = 1
            else:
                category = -1
            categoryName = "i"
        else:
            category = self.classSet.getId(categoryName)
        examples.append( (sentenceGraph.getSentenceId()+".x"+str(exampleIndex),category,features,extra) )