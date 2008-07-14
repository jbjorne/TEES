import sys
sys.path.append("..")
from Core.ExampleBuilder import ExampleBuilder

class SimpleDependencyExampleBuilder2(ExampleBuilder):
        
    def buildExamples(self, sentenceGraph):
        examples = []
        exampleIndex = 0
        dependencyEdges = sentenceGraph.dependencyGraph.edges()
        for depEdge in dependencyEdges:
            hasInt = sentenceGraph.interactionGraph.has_edge(depEdge[0], depEdge[1]) or sentenceGraph.interactionGraph.has_edge(depEdge[1], depEdge[0])
            if hasInt:
                category = 1
            else:
                category = -1
            features = self.buildFeatures(depEdge,sentenceGraph)
            if int(depEdge[0].attrib["id"].split("_")[-1]) < int(depEdge[1].attrib["id"].split("_")[-1]):
                extra = {"type":"edge","t1":depEdge[0],"t2":depEdge[1]}
            else:
                extra = {"type":"edge","t1":depEdge[1],"t2":depEdge[0]}
            examples.append( (sentenceGraph.getSentenceId()+".x"+str(exampleIndex),category,features,extra) )
            exampleIndex += 1
        return examples

    def buildFeatures(self, depEdge, sentenceGraph):
        features = {}
        features[self.featureSet.getId("dep_"+depEdge[2].attrib["type"])] = 1
        features[self.featureSet.getId("t1txt_"+sentenceGraph.getTokenText(depEdge[0]))] = 1
        features[self.featureSet.getId("t1POS_"+depEdge[0].attrib["POS"])] = 1
        features[self.featureSet.getId("t2txt_"+sentenceGraph.getTokenText(depEdge[1]))] = 1
        features[self.featureSet.getId("t2POS_"+depEdge[1].attrib["POS"])] = 1
        
        # Attached edges
        sentenceGraph
        
        # Linear order
#        if int(depEdge[0].attrib["id"].split("_")[-1]) < int(depEdge[1].attrib["id"].split("_")[-1]):
#            features[self.featureSet.getId("l1txt_"+sentenceGraph.getTokenText(depEdge[0]))] = 1
#            features[self.featureSet.getId("l1POS_"+depEdge[0].attrib["POS"])] = 1
#            features[self.featureSet.getId("l2txt_"+sentenceGraph.getTokenText(depEdge[1]))] = 1
#            features[self.featureSet.getId("l2POS_"+depEdge[1].attrib["POS"])] = 1
#        else:
#            features[self.featureSet.getId("l2txt_"+sentenceGraph.getTokenText(depEdge[0]))] = 1
#            features[self.featureSet.getId("l2POS_"+depEdge[0].attrib["POS"])] = 1
#            features[self.featureSet.getId("l1txt_"+sentenceGraph.getTokenText(depEdge[1]))] = 1
#            features[self.featureSet.getId("l1POS_"+depEdge[1].attrib["POS"])] = 1

        return features
