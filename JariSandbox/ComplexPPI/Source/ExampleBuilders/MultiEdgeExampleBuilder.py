import sys
sys.path.append("..")
from Core.ExampleBuilder import ExampleBuilder
from Core.IdSet import IdSet
from FeatureBuilders.MultiEdgeFeatureBuilder import MultiEdgeFeatureBuilder
import networkx as NX

class MultiEdgeExampleBuilder(ExampleBuilder):
    def __init__(self, styles=["typed","headsOnly"], length=[1,2,3], types=[]):
        ExampleBuilder.__init__(self)
        self.classSet = IdSet(1)
        assert( self.classSet.getId("neg") == 1 )
        self.multiEdgeFeatureBuilder = MultiEdgeFeatureBuilder(self.featureSet)
        self.styles = styles
        self.pathLengths = length
        self.types = types
     
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
                # find the path
                if paths.has_key(tI) and paths[tI].has_key(tJ):
                    path = paths[tI][tJ]
                elif paths.has_key(tJ) and paths[tJ].has_key(tI):
                    path = paths[tJ][tI]
                else:
                    continue
                if len(path) in self.pathLengths: #if len(path) > 1:#> 2:
                    # define class
                    if sentenceGraph.interactionGraph.has_edge(path[0], path[-1]):
                        intEdges = sentenceGraph.interactionGraph.get_edge(path[0], path[-1])
                        for intEdge in intEdges:
                            categoryName = intEdge.attrib["type"]                      
                            self.buildExample(path, sentenceGraph, categoryName, examples, exampleIndex)
                            exampleIndex += 1
                    else:
                        self.buildExample(path, sentenceGraph, "neg", examples, exampleIndex)
                        exampleIndex += 1
                    if sentenceGraph.interactionGraph.has_edge(path[-1], path[0]):
                        intEdges = sentenceGraph.interactionGraph.get_edge(path[-1], path[0])
                        for intEdge in intEdges:
                            categoryName = intEdge.attrib["type"]
                            self.buildExample(path[::-1], sentenceGraph, categoryName, examples, exampleIndex)
                            exampleIndex += 1
                    else:
                        self.buildExample(path[::-1], sentenceGraph, "neg", examples, exampleIndex)
                        exampleIndex += 1
        return examples
    
    def buildExample(self, path, sentenceGraph, categoryName, examples, exampleIndex):
        # define features
        features = {}
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
        # define extra attributes              
        if int(path[0].attrib["id"].split("_")[-1]) < int(path[-1].attrib["id"].split("_")[-1]):
            extra = {"xtype":"edge","type":"i","t1":path[0],"t2":path[-1]}
            extra["deprev"] = False
        else:
            extra = {"xtype":"edge","type":"i","t1":path[-1],"t2":path[0]}
            extra["deprev"] = True
        # make example
        category = self.classSet.getId(categoryName)
        examples.append( (sentenceGraph.getSentenceId()+".x"+str(exampleIndex),category,features,extra) )