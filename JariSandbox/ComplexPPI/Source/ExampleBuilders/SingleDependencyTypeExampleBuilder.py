import sys
sys.path.append("..")
from Core.ExampleBuilder import ExampleBuilder
#import Stemming.PorterStemmer as PorterStemmer
from Core.IdSet import IdSet

class SingleDependencyTypeExampleBuilder(ExampleBuilder):
    def __init__(self):
        ExampleBuilder.__init__(self)
        self.classSet = IdSet(1)
        assert( self.classSet.getId("neg") == 1 )

    def addType(self, token, features, sentenceGraph, prefix="annType_"):
        if sentenceGraph.tokenIsEntityHead[token] != None:
            features[self.featureSet.getId("annType_"+sentenceGraph.tokenIsEntityHead[token].attrib["type"])] = 1
        
    def buildExamples(self, sentenceGraph):
        examples = []
        exampleIndex = 0
        dependencyEdges = sentenceGraph.dependencyGraph.edges()
        for depEdge in dependencyEdges:
            if (sentenceGraph.tokenIsEntityHead[depEdge[0]] == None) or (sentenceGraph.tokenIsEntityHead[depEdge[1]] == None):
                continue

            if sentenceGraph.interactionGraph.has_edge(depEdge[0], depEdge[1]):
                categoryName = sentenceGraph.interactionGraph.get_edge(depEdge[0], depEdge[1]).attrib["type"]
                #categoryName += ">"
                category = self.classSet.getId(categoryName)
            elif sentenceGraph.interactionGraph.has_edge(depEdge[1], depEdge[0]):
                categoryName = sentenceGraph.interactionGraph.get_edge(depEdge[1], depEdge[0]).attrib["type"]
                #categoryName = "<" + categoryName
                categoryName += "_rev"
                category = self.classSet.getId(categoryName)
            else:
                categoryName = "neg"
                category = 1

            features = self.buildFeatures(depEdge,sentenceGraph)
            # Normalize features
#            total = 0.0
#            for v in features.values(): total += abs(v)
#            if total == 0.0: total = 1.0
#            for k,v in features.iteritems():
#                features[k] = float(v) / total
            # Define extra attributes f.e. for the visualizer
            if int(depEdge[0].attrib["id"].split("_")[-1]) < int(depEdge[1].attrib["id"].split("_")[-1]):
                extra = {"xtype":"edge","type":categoryName,"t1":depEdge[0],"t2":depEdge[1]}
                extra["deprev"] = False
            else:
#                if categoryName[0] == "<":
#                    categoryName = categoryName[1:] + ">"
#                elif categoryName[-1] == ">":
#                    categoryName = "<" + categoryName[:-1]
                extra = {"xtype":"edge","type":categoryName,"t1":depEdge[1],"t2":depEdge[0]}
                extra["deprev"] = True
            examples.append( (sentenceGraph.getSentenceId()+".x"+str(exampleIndex),category,features,extra) )
            exampleIndex += 1
        return examples

    def buildFeatures(self, depEdge, sentenceGraph):
        features = {}
        features[self.featureSet.getId("dep_"+depEdge[2].attrib["type"])] = 1
        # Token 1
        features[self.featureSet.getId("t1txt_"+sentenceGraph.getTokenText(depEdge[0]))] = 1
        #features[self.featureSet.getId("t1stem_"+PorterStemmer.stem(sentenceGraph.getTokenText(depEdge[0])))] = 1
        features[self.featureSet.getId("t1POS_"+depEdge[0].attrib["POS"])] = 1
        self.addType(depEdge[0], features, sentenceGraph, prefix="t1Ann_")
        # Token 2
        features[self.featureSet.getId("t2txt_"+sentenceGraph.getTokenText(depEdge[1]))] = 1
        #features[self.featureSet.getId("t2stem_"+PorterStemmer.stem(sentenceGraph.getTokenText(depEdge[1])))] = 1
        features[self.featureSet.getId("t2POS_"+depEdge[1].attrib["POS"])] = 1
        self.addType(depEdge[1], features, sentenceGraph, prefix="t2Ann_")
        
        # Attached edges
        t1InEdges = sentenceGraph.dependencyGraph.in_edges(depEdge[0])
        for edge in t1InEdges:
            features[self.featureSet.getId("t1HangingIn_"+edge[2].attrib["type"])] = 1
            features[self.featureSet.getId("t1HangingIn_"+edge[0].attrib["POS"])] = 1
            self.addType(edge[0], features, sentenceGraph, prefix="t1HangingInAnn_")
            #features[self.featureSet.getId("t1HangingIn_"+sentenceGraph.getTokenText(edge[0]))] = 1
        t1OutEdges = sentenceGraph.dependencyGraph.out_edges(depEdge[0])
        for edge in t1OutEdges:
            features[self.featureSet.getId("t1HangingOut_"+edge[2].attrib["type"])] = 1
            features[self.featureSet.getId("t1HangingOut_"+edge[1].attrib["POS"])] = 1
            self.addType(edge[1], features, sentenceGraph, prefix="t1HangingOutAnn_")
            #features[self.featureSet.getId("t1HangingOut_"+sentenceGraph.getTokenText(edge[1]))] = 1
        
        t2InEdges = sentenceGraph.dependencyGraph.in_edges(depEdge[1])
        for edge in t2InEdges:
            features[self.featureSet.getId("t2HangingIn_"+edge[2].attrib["type"])] = 1
            features[self.featureSet.getId("t2HangingIn_"+edge[0].attrib["POS"])] = 1
            self.addType(edge[0], features, sentenceGraph, prefix="t2HangingInAnn_")
            #features[self.featureSet.getId("t2HangingIn_"+sentenceGraph.getTokenText(edge[0]))] = 1
        t2OutEdges = sentenceGraph.dependencyGraph.out_edges(depEdge[1])
        for edge in t2OutEdges:
            features[self.featureSet.getId("t2HangingOut_"+edge[2].attrib["type"])] = 1
            features[self.featureSet.getId("t2HangingOut_"+edge[1].attrib["POS"])] = 1
            self.addType(edge[1], features, sentenceGraph, prefix="t2HangingOutAnn_")
            #features[self.featureSet.getId("t2HangingOut_"+sentenceGraph.getTokenText(edge[1]))] = 1
        
        # Linear order
#        t1Position = int(depEdge[0].attrib["id"].split("_")[-1])
#        t2Position = int(depEdge[1].attrib["id"].split("_")[-1])
#        features[self.featureSet.getId("lin_distance")] = t2Position - t1Position

#        if t1Position < t2Position:
#            features[self.featureSet.getId("forward")] = 1
#            features[self.featureSet.getId("lin_distance")] = t2Position - t1Position
#            #features[self.featureSet.getId("l1txt_"+sentenceGraph.getTokenText(depEdge[0]))] = 1
#            #features[self.featureSet.getId("l1POS_"+depEdge[0].attrib["POS"])] = 1
#            #features[self.featureSet.getId("l2txt_"+sentenceGraph.getTokenText(depEdge[1]))] = 1
#            #features[self.featureSet.getId("l2POS_"+depEdge[1].attrib["POS"])] = 1
#        else:
#            features[self.featureSet.getId("reverse")] = 1
#            features[self.featureSet.getId("lin_distance")] = t2Position - t1Position
#            #features[self.featureSet.getId("l2txt_"+sentenceGraph.getTokenText(depEdge[0]))] = 1
#            #features[self.featureSet.getId("l2POS_"+depEdge[0].attrib["POS"])] = 1
#            #features[self.featureSet.getId("l1txt_"+sentenceGraph.getTokenText(depEdge[1]))] = 1
#            #features[self.featureSet.getId("l1POS_"+depEdge[1].attrib["POS"])] = 1

        return features
