import sys
sys.path.append("..")
from Core.ExampleBuilder import ExampleBuilder
#import Stemming.PorterStemmer as PorterStemmer

class SimpleDependencyExampleBuilder2(ExampleBuilder):
        
    def buildExamples(self, sentenceGraph):
        examples = []
        exampleIndex = 0
        dependencyEdges = sentenceGraph.dependencyGraph.edges()
        for depEdge in dependencyEdges:
            if (sentenceGraph.tokenIsEntityHead[depEdge[0]] == None) or (sentenceGraph.tokenIsEntityHead[depEdge[1]] == None):
                continue
            hasInt = sentenceGraph.interactionGraph.has_edge(depEdge[0], depEdge[1]) or sentenceGraph.interactionGraph.has_edge(depEdge[1], depEdge[0])
            if hasInt:
                category = 1
            else:
                category = -1
            features = self.buildFeatures(depEdge,sentenceGraph)
            # Normalize features
#            total = 0.0
#            for v in features.values(): total += abs(v)
#            if total == 0.0: total = 1.0
#            for k,v in features.iteritems():
#                features[k] = float(v) / total
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
        features[self.featureSet.getId("dep_"+depEdge[2].attrib["type"])] = 1
        # Token 1
        features[self.featureSet.getId("t1txt_"+sentenceGraph.getTokenText(depEdge[0]))] = 1
        #features[self.featureSet.getId("t1stem_"+PorterStemmer.stem(sentenceGraph.getTokenText(depEdge[0])))] = 1
        features[self.featureSet.getId("t1POS_"+depEdge[0].attrib["POS"])] = 1
        features[self.featureSet.getId("t1AnnType_"+sentenceGraph.tokenIsEntityHead[depEdge[0]].attrib["type"])] = 1
        # Token 2
        features[self.featureSet.getId("t2txt_"+sentenceGraph.getTokenText(depEdge[1]))] = 1
        #features[self.featureSet.getId("t2stem_"+PorterStemmer.stem(sentenceGraph.getTokenText(depEdge[1])))] = 1
        features[self.featureSet.getId("t2POS_"+depEdge[1].attrib["POS"])] = 1
        features[self.featureSet.getId("t2AnnType_"+sentenceGraph.tokenIsEntityHead[depEdge[1]].attrib["type"])] = 1
        
        # Attached edges
        t1InEdges = sentenceGraph.dependencyGraph.in_edges(depEdge[0])
        for edge in t1InEdges:
            features[self.featureSet.getId("t1HangingIn_"+edge[2].attrib["type"])] = 1
            features[self.featureSet.getId("t1HangingIn_"+edge[0].attrib["POS"])] = 1
            if sentenceGraph.tokenIsEntityHead[edge[0]] != None:
                features[self.featureSet.getId("t1HangingIn_AnnType_"+sentenceGraph.tokenIsEntityHead[edge[0]].attrib["type"])] = 1
            #features[self.featureSet.getId("t1HangingIn_"+sentenceGraph.getTokenText(edge[0]))] = 1
        t1OutEdges = sentenceGraph.dependencyGraph.out_edges(depEdge[0])
        for edge in t1OutEdges:
            features[self.featureSet.getId("t1HangingOut_"+edge[2].attrib["type"])] = 1
            features[self.featureSet.getId("t1HangingOut_"+edge[1].attrib["POS"])] = 1
            if sentenceGraph.tokenIsEntityHead[edge[1]] != None:
                features[self.featureSet.getId("t1HangingOut_AnnType_"+sentenceGraph.tokenIsEntityHead[edge[1]].attrib["type"])] = 1
            #features[self.featureSet.getId("t1HangingOut_"+sentenceGraph.getTokenText(edge[1]))] = 1
        
        t2InEdges = sentenceGraph.dependencyGraph.in_edges(depEdge[1])
        for edge in t2InEdges:
            features[self.featureSet.getId("t2HangingIn_"+edge[2].attrib["type"])] = 1
            features[self.featureSet.getId("t2HangingIn_"+edge[0].attrib["POS"])] = 1
            #features[self.featureSet.getId("t2HangingIn_"+sentenceGraph.getTokenText(edge[0]))] = 1
            if sentenceGraph.tokenIsEntityHead[edge[0]] != None:
                features[self.featureSet.getId("t2HangingIn_AnnType_"+sentenceGraph.tokenIsEntityHead[edge[0]].attrib["type"])] = 1
        t2OutEdges = sentenceGraph.dependencyGraph.out_edges(depEdge[1])
        for edge in t2OutEdges:
            features[self.featureSet.getId("t2HangingOut_"+edge[2].attrib["type"])] = 1
            features[self.featureSet.getId("t2HangingOut_"+edge[1].attrib["POS"])] = 1
            if sentenceGraph.tokenIsEntityHead[edge[1]] != None:
                features[self.featureSet.getId("t2HangingIn_AnnType_"+sentenceGraph.tokenIsEntityHead[edge[1]].attrib["type"])] = 1
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
