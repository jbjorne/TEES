import sys
sys.path.append("..")
from Core.ExampleBuilder import ExampleBuilder
from Core.IdSet import IdSet
#import Stemming.PorterStemmer as PorterStemmer
import networkx as NX

class TokenRoleMultiEdgeTypeExampleBuilder(ExampleBuilder):
    def __init__(self):
        ExampleBuilder.__init__(self)
        self.classSet = IdSet(1)
        assert( self.classSet.getId("neg") == 1 )
    
    # Results slightly nondeterministic because when there are multiple edges between two
    # tokens, this currently returns only one, and their order is not defined.
    def getEdges(self, graph, path):
        pathEdges = []
        edges = graph.edges()
        for i in range(1, len(path)):
            found = False
            for edge in edges:
                if edge[0] == path[i-1] and edge[1] == path[i]:
                    pathEdges.append((edge, True))
                    found = True
                elif edge[1] == path[i-1] and edge[0] == path[i]:
                    pathEdges.append((edge, False))
                    found = True
                if found == True:
                    break
            assert(found==True)
        return pathEdges
    
    def addType(self, token, features, sentenceGraph, prefix="annType_"):
        if sentenceGraph.tokenIsEntityHead[token] != None:
            features[self.featureSet.getId("annType_"+sentenceGraph.tokenIsEntityHead[token].attrib["type"])] = 1
     
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
                if (sentenceGraph.tokenIsEntityHead[tI] == None) or (sentenceGraph.tokenIsEntityHead[tJ] == None):
                    continue
                # find the path
                if paths.has_key(tI) and paths[tI].has_key(tJ):
                    path = paths[tI][tJ]
                elif paths.has_key(tJ) and paths[tJ].has_key(tI):
                    path = paths[tJ][tI]
                else:
                    continue
                if len(path) > 2:
                    # define class
                    if sentenceGraph.interactionGraph.has_edge(path[0], path[-1]):
                        categoryName = sentenceGraph.interactionGraph.get_edge(path[0], path[-1]).attrib["type"]                      
                        self.buildExample(path, sentenceGraph, categoryName, examples, exampleIndex)
                        exampleIndex += 1
                    else:
                        self.buildExample(path, sentenceGraph, "neg", examples, exampleIndex)
                        exampleIndex += 1
                    if sentenceGraph.interactionGraph.has_edge(path[-1], path[0]):
                        categoryName = sentenceGraph.interactionGraph.get_edge(path[-1], path[0]).attrib["type"]
                        categoryName += "_rev"
                        self.buildExample(path[::-1], sentenceGraph, categoryName, examples, exampleIndex)
                        exampleIndex += 1
                    else:
                        self.buildExample(path[::-1], sentenceGraph, "neg", examples, exampleIndex)
                        exampleIndex += 1
        return examples
    
    def buildExample(self, path, sentenceGraph, categoryName, examples, exampleIndex):
        # define features
        features = {}
        edges = self.getEdges(sentenceGraph.dependencyGraph, path)
        features[self.featureSet.getId("len_edges_"+str(len(edges)))] = 1
        features[self.featureSet.getId("len")] = len(edges)
        self.buildPathRoleFeatures(path, edges, sentenceGraph, features)
        self.buildEdgeCombinations(edges, sentenceGraph, features)
        #self.buildTerminusFeatures(path[0], "t1", sentenceGraph, features)
        #self.buildTerminusFeatures(path[-1], "t2", sentenceGraph, features)
        for edge in edges:
            self.buildPathEdgeFeatures(edge[0], sentenceGraph, features)
#        if edges[0][0][0] == path[0]:
#            t1 = edges[0][0][0]
#        else:
#            t1 = edges[0][0][1]
#            assert(edges[0][0][1] == path[0])
#        if edges[-1][0][0] == path[-1]:
#            t2 = edges[-1][0][0]
#        else:
#            t2 = edges[-1][0][1]
#            assert(edges[-1][0][1] == path[-1])
#        self.buildEdgeCombinations(edges, sentenceGraph, features)
#        self.buildTerminusFeatures(t1, t2, sentenceGraph, features)
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
    
    def buildPathRoleFeatures(self, pathTokens, pathEdges, sentenceGraph, features):
        #print len(pathTokens), len(pathEdges)
        features[self.featureSet.getId("tokTerm1POS_"+pathTokens[0].attrib["POS"])] = 1
        features[self.featureSet.getId("tokTerm1txt_"+sentenceGraph.getTokenText(pathTokens[0]))] = 1
        features[self.featureSet.getId("tokTerm2POS_"+pathTokens[-1].attrib["POS"])] = 1
        features[self.featureSet.getId("tokTerm2txt_"+sentenceGraph.getTokenText(pathTokens[-1]))] = 1
#        for i in range(0,len(pathEdges)):
#            if pathEdges[i][1]:
#                features[self.featureSet.getId("depRight_"+pathEdges[i][0][2].attrib["type"])] = 1
#            else:
#                features[self.featureSet.getId("depLeft_"+pathEdges[i][0][2].attrib["type"])] = 1
        for i in range(1,len(pathEdges)):
            if pathEdges[i-1][1] and pathEdges[i][1]:
                features[self.featureSet.getId("depRight1_"+pathEdges[i-1][0][2].attrib["type"])] = 1
                features[self.featureSet.getId("depRight2_"+pathEdges[i][0][2].attrib["type"])] = 1
                features[self.featureSet.getId("tokRightPOS_"+pathTokens[i].attrib["POS"])] = 1
                features[self.featureSet.getId("tokRightTxt_"+sentenceGraph.getTokenText(pathTokens[i]))] = 1
            elif (not pathEdges[i-1][1]) and (not pathEdges[i][1]):
                features[self.featureSet.getId("depLeft1_"+pathEdges[i-1][0][2].attrib["type"])] = 1
                features[self.featureSet.getId("depLeft2_"+pathEdges[i][0][2].attrib["type"])] = 1
                features[self.featureSet.getId("tokLeftPOS_"+pathTokens[i].attrib["POS"])] = 1
                features[self.featureSet.getId("tokLeftTxt_"+sentenceGraph.getTokenText(pathTokens[i]))] = 1
            elif (not pathEdges[i-1][1]) and pathEdges[i][1]:
                features[self.featureSet.getId("depTop1_"+pathEdges[i-1][0][2].attrib["type"])] = 1
                features[self.featureSet.getId("depTop2_"+pathEdges[i][0][2].attrib["type"])] = 1
                features[self.featureSet.getId("tokTopPOS_"+pathTokens[i].attrib["POS"])] = 1
                features[self.featureSet.getId("tokTopTxt_"+sentenceGraph.getTokenText(pathTokens[i]))] = 1
            elif pathEdges[i-1][1] and (not pathEdges[i][1]):
                features[self.featureSet.getId("depBottom1_"+pathEdges[i-1][0][2].attrib["type"])] = 1
                features[self.featureSet.getId("depBottom2_"+pathEdges[i][0][2].attrib["type"])] = 1
                features[self.featureSet.getId("tokBottomPOS_"+pathTokens[i].attrib["POS"])] = 1
                features[self.featureSet.getId("tokBottomTxt_"+sentenceGraph.getTokenText(pathTokens[i]))] = 1
    
    def buildPathEdgeFeatures(self, depEdge, sentenceGraph, features):
        depType = depEdge[2].attrib["type"]
        features[self.featureSet.getId("dep_"+depType)] = 1
        # Token 1
        features[self.featureSet.getId("txt_"+sentenceGraph.getTokenText(depEdge[0]))] = 1
        features[self.featureSet.getId("POS_"+depEdge[0].attrib["POS"])] = 1
        self.addType(depEdge[0], features, sentenceGraph, prefix="annType_")
        # Token 2
        features[self.featureSet.getId("txt_"+sentenceGraph.getTokenText(depEdge[1]))] = 1
        features[self.featureSet.getId("POS_"+depEdge[1].attrib["POS"])] = 1
        self.addType(depEdge[1], features, sentenceGraph, prefix="annType_")
    
    def buildEdgeCombinations(self, edges, sentenceGraph, features):
        # Edges directed relative to the path
        for i in range(len(edges)):
            depType = edges[i][0][2].attrib["type"]
            if edges[i][1]:
                features[self.featureSet.getId("dep_"+depType+">")] = 1
            else:
                features[self.featureSet.getId("dep_<"+depType)] = 1
        # Edge bigrams
        if edges[0][1]:
            features[self.featureSet.getId("internalPOS_"+edges[0][0][0].attrib["POS"])]=1
            features[self.featureSet.getId("internalTxt_"+sentenceGraph.getTokenText(edges[0][0][0]))]=1
        else:
            features[self.featureSet.getId("internalPOS_"+edges[0][0][1].attrib["POS"])]=1
            features[self.featureSet.getId("internalTxt_"+sentenceGraph.getTokenText(edges[0][0][1]))]=1
        if edges[-1][1]:
            features[self.featureSet.getId("internalPOS_"+edges[-1][0][1].attrib["POS"])]=1
            features[self.featureSet.getId("internalTxt_"+sentenceGraph.getTokenText(edges[-1][0][1]))]=1
        else:
            features[self.featureSet.getId("internalPOS_"+edges[-1][0][0].attrib["POS"])]=1
            features[self.featureSet.getId("internalTxt_"+sentenceGraph.getTokenText(edges[-1][0][0]))]=1
        for i in range(1,len(edges)-1):
            features[self.featureSet.getId("internalPOS_"+edges[i][0][0].attrib["POS"])]=1
            features[self.featureSet.getId("internalTxt_"+sentenceGraph.getTokenText(edges[i][0][0]))]=1
            features[self.featureSet.getId("internalPOS_"+edges[i][0][1].attrib["POS"])]=1
            features[self.featureSet.getId("internalTxt_"+sentenceGraph.getTokenText(edges[i][0][1]))]=1
            features[self.featureSet.getId("internalDep_"+edges[i][0][2].attrib["type"])]=1
        for i in range(1,len(edges)):
            type1 = edges[i-1][0][2].attrib["type"]
            type2 = edges[i][0][2].attrib["type"]
            if edges[i-1][1] and edges[i][1]:
                features[self.featureSet.getId("dep_"+type1+">"+type2+">")] = 1
            elif edges[i-1][1] and edges[i][0]:
                features[self.featureSet.getId("dep_"+type1+">"+type2+"<")] = 1
            elif edges[i-1][0] and edges[i][0]:
                features[self.featureSet.getId("dep_"+type1+"<"+type2+"<")] = 1
            elif edges[i-1][0] and edges[i][1]:
                features[self.featureSet.getId("dep_"+type1+"<"+type2+">")] = 1
   
    def buildTerminusFeatures(self, token, prefix, sentenceGraph, features): 
        # Attached edges
        t1InEdges = sentenceGraph.dependencyGraph.in_edges(token)
        for edge in t1InEdges:
            features[self.featureSet.getId(prefix+"HangingIn_"+edge[2].attrib["type"])] = 1
            features[self.featureSet.getId(prefix+"HangingIn_"+edge[0].attrib["POS"])] = 1
            features[self.featureSet.getId("t1HangingIn_"+sentenceGraph.getTokenText(edge[0]))] = 1
        t1OutEdges = sentenceGraph.dependencyGraph.out_edges(token)
        for edge in t1OutEdges:
            features[self.featureSet.getId(prefix+"HangingOut_"+edge[2].attrib["type"])] = 1
            features[self.featureSet.getId(prefix+"HangingOut_"+edge[1].attrib["POS"])] = 1
            features[self.featureSet.getId("t1HangingOut_"+sentenceGraph.getTokenText(edge[1]))] = 1
        
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
