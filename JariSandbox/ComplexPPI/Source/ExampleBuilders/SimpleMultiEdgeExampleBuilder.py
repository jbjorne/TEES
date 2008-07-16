import sys
sys.path.append("..")
from Core.ExampleBuilder import ExampleBuilder
#import Stemming.PorterStemmer as PorterStemmer
import networkx as NX

class SimpleMultiEdgeExampleBuilder(ExampleBuilder):
    
    def getEdges(self, graph, path):
        for i in range(1, len(path)):
            edge = graph.get_edge(path[i-1],path[i])
            isReverse = False
            if edge == None:
                graph.get_edge(path[i],path[i-1])
                isReverse = True
            assert(edge != None)
            edges.append( (edge, isReverse) )
        return edges
    
    def processGraph(self, sentenceGraph):
        undirected = sentenceGraph.dependencyGraph.to_undirected()
        paths = NX.all_pairs_shortest_path(undirected, cutoff=4)
        #key1 = paths.keys()[0]
        #key2 = paths[key1].keys()[0]
        #print key1
        #print key2
        #print paths[key1][key2]
        #sys.exit(0)
        for i in range(len(sentenceGraph.tokens)-1):
            for j in range(i+1,len(sentenceGraph.tokens)):
                path = paths[i][j]
                if len(path) > 2:
                    edges = getEdges(path)
        
    def buildExamples(self, sentenceGraph):
        examples = []
        exampleIndex = 0
        
        #self.processGraph(sentenceGraph)
        
        dependencyEdges = sentenceGraph.dependencyGraph.edges()
        for depEdge in dependencyEdges:
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
                extra = {"type":"edge","t1":depEdge[0],"t2":depEdge[1]}
            else:
                extra = {"type":"edge","t1":depEdge[1],"t2":depEdge[0]}
            examples.append( (sentenceGraph.getSentenceId()+".x"+str(exampleIndex),category,features,extra) )
            exampleIndex += 1
        return examples

    def buildPathEdgeFeatures(self, depEdge, sentenceGraph):
        features = {}
        depType = depEdge[2].attrib["type"]
        features[self.featureSet.getId("dep_"+depType)] = 1
        # Token 1
        features[self.featureSet.getId("txt_"+sentenceGraph.getTokenText(depEdge[0])+"_"+depType)] = 1
        features[self.featureSet.getId("POS_"+depEdge[0].attrib["POS"]+"_"+depType)] = 1
        # Token 2
        features[self.featureSet.getId("txt_"+depType+"_"+sentenceGraph.getTokenText(depEdge[1]))] = 1
        features[self.featureSet.getId("POS_"+depType+"_"+depEdge[1].attrib["POS"])] = 1
   
    def buildTerminusFeatures(self, t1, t2): 
        # Attached edges
        t1InEdges = sentenceGraph.dependencyGraph.in_edges(t1)
        for edge in t1InEdges:
            features[self.featureSet.getId("t1HangingIn_"+edge[2].attrib["type"])] = 1
            features[self.featureSet.getId("t1HangingIn_"+edge[0].attrib["POS"])] = 1
            #features[self.featureSet.getId("t1HangingIn_"+sentenceGraph.getTokenText(edge[0]))] = 1
        t1OutEdges = sentenceGraph.dependencyGraph.out_edges(depEdge[0])
        for edge in t1OutEdges:
            features[self.featureSet.getId("t1HangingOut_"+edge[2].attrib["type"])] = 1
            features[self.featureSet.getId("t1HangingOut_"+edge[1].attrib["POS"])] = 1
            #features[self.featureSet.getId("t1HangingOut_"+sentenceGraph.getTokenText(edge[1]))] = 1
        
        t2InEdges = sentenceGraph.dependencyGraph.in_edges(t1)
        for edge in t2InEdges:
            features[self.featureSet.getId("t2HangingIn_"+edge[2].attrib["type"])] = 1
            features[self.featureSet.getId("t2HangingIn_"+edge[0].attrib["POS"])] = 1
            #features[self.featureSet.getId("t2HangingIn_"+sentenceGraph.getTokenText(edge[0]))] = 1
        t2OutEdges = sentenceGraph.dependencyGraph.out_edges(depEdge[1])
        for edge in t2OutEdges:
            features[self.featureSet.getId("t2HangingOut_"+edge[2].attrib["type"])] = 1
            features[self.featureSet.getId("t2HangingOut_"+edge[1].attrib["POS"])] = 1
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
