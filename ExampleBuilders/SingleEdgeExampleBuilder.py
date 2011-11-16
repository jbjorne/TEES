import sys
sys.path.append("..")
from Core.ExampleBuilder import ExampleBuilder
from Core.IdSet import IdSet
from FeatureBuilders.EdgeFeatureBuilder import EdgeFeatureBuilder

class SingleEdgeExampleBuilder(ExampleBuilder):
    """
    Builds examples based on parse dependencies. An example is generated for each dependency. 
    If there is an annotated interaction edge between those tokens, then the example is positive,
    otherwise negative. Optionally examples can be generated only between tokens that are heads
    of entities.
    """
    def __init__(self, style):
        ExampleBuilder.__init__(self)
        self.featureBuilder = EdgeFeatureBuilder(self.featureSet)
        self.style = style
        if not "binary" in style:
            self.classSet = IdSet(1)
            assert( self.classSet.getId("neg") == 1 )
        
    def buildExamples(self, sentenceGraph):
        examples = []
        exampleIndex = 0
        dependencyEdges = sentenceGraph.dependencyGraph.edges()
        for depEdge in dependencyEdges:
            if "headsOnly" in self.style:
                if (sentenceGraph.tokenIsEntityHead[depEdge[0]] == None) or (sentenceGraph.tokenIsEntityHead[depEdge[1]] == None):
                    continue
            
            edgeFound = False
            if sentenceGraph.interactionGraph.has_edge(depEdge[0], depEdge[1]):
                intEdges = sentenceGraph.interactionGraph.get_edge(depEdge[0], depEdge[1])
                for intEdge in intEdges:
                    examples.append( self.buildExample(depEdge, intEdge, False, exampleIndex, sentenceGraph) )
                    exampleIndex += 1
                    edgeFound = True
            elif "directed" in self.style:
                examples.append( self.buildExample(depEdge, None, None, exampleIndex, sentenceGraph) )
                exampleIndex += 1
            if sentenceGraph.interactionGraph.has_edge(depEdge[1], depEdge[0]):
                intEdges = sentenceGraph.interactionGraph.get_edge(depEdge[1], depEdge[0])
                for intEdge in intEdges:
                    examples.append( self.buildExample(depEdge, intEdge, True, exampleIndex, sentenceGraph) )
                    exampleIndex += 1
                    edgeFound = True
            elif "directed" in self.style:
                examples.append( self.buildExample(depEdge, None, None, exampleIndex, sentenceGraph) )
                exampleIndex += 1
            
            if (not edgeFound) and (not "directed" in self.style):
                examples.append( self.buildExample(depEdge, None, None, exampleIndex, sentenceGraph) )
                exampleIndex += 1

        return examples
    
    def buildExample(self, depEdge, intEdge, isReverse, exampleIndex, sentenceGraph):
        if "binary" in self.style:
            categoryName = "i"
            if intEdge != None:
                category = 1
            else:
                category = -1
        else:
            if intEdge != None:
                categoryName = intEdge.attrib["type"]
                if isReverse and "directed" in self.style:
                    categoryName += "_rev"
                category = self.classSet.getId(categoryName)
            else:
                categoryName = "neg"
                category = 1
        
        features = self.buildFeatures(depEdge,sentenceGraph)

        # Define extra attributes f.e. for the visualizer
        if int(depEdge[0].attrib["id"].split("_")[-1]) < int(depEdge[1].attrib["id"].split("_")[-1]):
            extra = {"xtype":"edge","type":categoryName,"t1":depEdge[0],"t2":depEdge[1]}
            extra["deprev"] = False
        else:
            extra = {"xtype":"edge","type":categoryName,"t1":depEdge[1],"t2":depEdge[0]}
            extra["deprev"] = True
        return (sentenceGraph.getSentenceId()+".x"+str(exampleIndex),category,features,extra)

    def buildFeatures(self, depEdge, sentenceGraph):
        features = {}
        self.featureBuilder.setFeatureVector(features)
        self.featureBuilder.buildEdgeFeatures(depEdge, sentenceGraph, "dep_", text=True, POS=True, annType=True, maskNames=True)
        self.featureBuilder.buildAttachedEdgeFeatures(depEdge, sentenceGraph, "", text=False, POS=True, annType=False, maskNames=True)       
        self.featureBuilder.buildLinearOrderFeatures(depEdge)
        self.featureBuilder.setFeatureVector(None)
        return features
