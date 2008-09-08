import sys
sys.path.append("..")
from Core.ExampleBuilder import ExampleBuilder
from FeatureBuilders.EdgeFeatureBuilder import EdgeFeatureBuilder

class SimpleDependencyExampleBuilder2(ExampleBuilder):
    """
    Builds examples based on parse dependencies. An example is generated for each dependency. 
    If there is an annotated interaction edge between those tokens, then the example is positive,
    otherwise negative.
    """
    def __init__(self):
        ExampleBuilder.__init__(self)
        self.featureBuilder = EdgeFeatureBuilder(self.featureSet)
        
    def buildExamples(self, sentenceGraph):
        examples = []
        exampleIndex = 0
        dependencyEdges = sentenceGraph.dependencyGraph.edges()
        # Loop through all the dependencies in the sentence
        for depEdge in dependencyEdges:
            # Ignore dependencies that do not connect annotated entities
#            if (sentenceGraph.tokenIsEntityHead[depEdge[0]] == None) or (sentenceGraph.tokenIsEntityHead[depEdge[1]] == None):
#                continue
            # Dependencies that have a corresponding interaction edge (direction is ignored) are the positive cases
            if sentenceGraph.interactionGraph.has_edge(depEdge[0], depEdge[1]) or sentenceGraph.interactionGraph.has_edge(depEdge[1], depEdge[0]):
                category = 1
            else:
                category = -1
            # Generate features for the edge
            features = self.buildFeatures(depEdge,sentenceGraph)
            # Define extra attributes f.e. for the visualizer
            if int(depEdge[0].attrib["id"].split("_")[-1]) < int(depEdge[1].attrib["id"].split("_")[-1]):
                extra = {"xtype":"edge","type":"i","t1":depEdge[0],"t2":depEdge[1]}
            else:
                extra = {"xtype":"edge","type":"i","t1":depEdge[1],"t2":depEdge[0]}
            examples.append( (sentenceGraph.getSentenceId()+".x"+str(exampleIndex),category,features,extra) )
            exampleIndex += 1
        return examples

    def buildFeatures(self, depEdge, sentenceGraph):
        features = {}
        self.featureBuilder.setFeatureVector(features)
        self.featureBuilder.buildEdgeFeatures(depEdge, sentenceGraph, "dep_", text=True, POS=True, annType=True, maskNames=True)
        self.featureBuilder.buildAttachedEdgeFeatures(depEdge, sentenceGraph, "", text=False, POS=True, annType=False, maskNames=True)       
        self.featureBuilder.buildLinearOrderFeatures(depEdge)
        self.featureBuilder.setFeatureVector(None)
        return features
