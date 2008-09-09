import sys
sys.path.append("..")
from Core.ExampleBuilder import ExampleBuilder
from Core.IdSet import IdSet
from FeatureBuilders.EdgeFeatureBuilder import EdgeFeatureBuilder

class SingleDependencyTypeExampleBuilder(ExampleBuilder):
    def __init__(self):
        ExampleBuilder.__init__(self)
        self.classSet = IdSet(1)
        assert( self.classSet.getId("neg") == 1 )
        self.featureBuilder = EdgeFeatureBuilder(self.featureSet)
        
    def buildExamples(self, sentenceGraph):
        examples = []
        exampleIndex = 0
        dependencyEdges = sentenceGraph.dependencyGraph.edges()
        for depEdge in dependencyEdges:
            if (sentenceGraph.tokenIsEntityHead[depEdge[0]] == None) or (sentenceGraph.tokenIsEntityHead[depEdge[1]] == None):
                continue
            
            if sentenceGraph.interactionGraph.has_edge(depEdge[0], depEdge[1]):
                intEdges = sentenceGraph.interactionGraph.get_edge(depEdge[0], depEdge[1])
                for intEdge in intEdges:
                    examples.append( self.buildExample(depEdge, intEdge, False, exampleIndex, sentenceGraph) )
                    exampleIndex += 1
            elif sentenceGraph.interactionGraph.has_edge(depEdge[1], depEdge[0]):
                intEdges = sentenceGraph.interactionGraph.get_edge(depEdge[1], depEdge[0])
                for intEdge in intEdges:
                    examples.append( self.buildExample(depEdge, intEdge, True, exampleIndex, sentenceGraph) )
                    exampleIndex += 1
            else:
                examples.append( self.buildExample(depEdge, None, None, exampleIndex, sentenceGraph) )
                exampleIndex += 1

        return examples
    
    def buildExample(self, depEdge, intEdge, isReverse, exampleIndex, sentenceGraph):
        if intEdge != None:
            categoryName = intEdge.attrib["type"]
            if isReverse:
                categoryName += "_rev"
            #categoryName += ">"
            #categoryName = "<" + categoryName
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
        
        # Attached edges
        self.featureBuilder.buildAttachedEdgeFeatures(depEdge, sentenceGraph, "", text=False, POS=True, annType=False, maskNames=True)               
#        t1InEdges = sentenceGraph.dependencyGraph.in_edges(depEdge[0])
#        for edge in t1InEdges:
#            features[self.featureSet.getId("t1HangingIn_"+edge[2].attrib["type"])] = 1
#            features[self.featureSet.getId("t1HangingIn_"+edge[0].attrib["POS"])] = 1
#            self.addType(edge[0], features, sentenceGraph, prefix="t1HangingInAnn_")
#            #features[self.featureSet.getId("t1HangingIn_"+sentenceGraph.getTokenText(edge[0]))] = 1
#        t1OutEdges = sentenceGraph.dependencyGraph.out_edges(depEdge[0])
#        for edge in t1OutEdges:
#            features[self.featureSet.getId("t1HangingOut_"+edge[2].attrib["type"])] = 1
#            features[self.featureSet.getId("t1HangingOut_"+edge[1].attrib["POS"])] = 1
#            self.addType(edge[1], features, sentenceGraph, prefix="t1HangingOutAnn_")
#            #features[self.featureSet.getId("t1HangingOut_"+sentenceGraph.getTokenText(edge[1]))] = 1
#        
#        t2InEdges = sentenceGraph.dependencyGraph.in_edges(depEdge[1])
#        for edge in t2InEdges:
#            features[self.featureSet.getId("t2HangingIn_"+edge[2].attrib["type"])] = 1
#            features[self.featureSet.getId("t2HangingIn_"+edge[0].attrib["POS"])] = 1
#            self.addType(edge[0], features, sentenceGraph, prefix="t2HangingInAnn_")
#            #features[self.featureSet.getId("t2HangingIn_"+sentenceGraph.getTokenText(edge[0]))] = 1
#        t2OutEdges = sentenceGraph.dependencyGraph.out_edges(depEdge[1])
#       for edge in t2OutEdges:
#            features[self.featureSet.getId("t2HangingOut_"+edge[2].attrib["type"])] = 1
#            features[self.featureSet.getId("t2HangingOut_"+edge[1].attrib["POS"])] = 1
#            self.addType(edge[1], features, sentenceGraph, prefix="t2HangingOutAnn_")
#            #features[self.featureSet.getId("t2HangingOut_"+sentenceGraph.getTokenText(edge[1]))] = 1
        
        # Linear order
        self.featureBuilder.buildLinearOrderFeatures(depEdge)
        self.featureBuilder.setFeatureVector(None)
        return features
