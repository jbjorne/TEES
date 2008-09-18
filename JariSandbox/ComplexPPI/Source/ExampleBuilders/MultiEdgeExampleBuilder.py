import sys
sys.path.append("..")
from Core.ExampleBuilder import ExampleBuilder
from Core.IdSet import IdSet
import networkx as NX

class MultiEdgeExampleBuilder(ExampleBuilder):
    def __init__(self, styles=["typed","headsOnly"], length=[1,2,3], ignore=[]):
        ExampleBuilder.__init__(self)
        self.classSet = IdSet(1)
        assert( self.classSet.getId("neg") == 1 )
    
    # Results slightly nondeterministic because when there are multiple edges between two
    # tokens, this currently returns only one, and their order is not defined.
    def getEdges(self, graph, path):
        pathEdges = {}
        for i in range(0, len(path)):
            pathEdges[i] = {}
        for i in range(1, len(path)):
            pathEdges[i][i-1] = []
            pathEdges[i-1][i] = []
        edges = graph.edges()
        for i in range(1, len(path)):
            found = False
            for edge in edges:
                if edge[0] == path[i-1] and edge[1] == path[i]:
                    pathEdges[i-1][i].append(edge)
                    found = True
                elif edge[1] == path[i-1] and edge[0] == path[i]:
                    pathEdges[i][i-1].append(edge)
                    found = True
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
                # if len(path) in self.pathLengths:
                if len(path) > 1:#> 2:
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
        edges = self.getEdges(sentenceGraph.dependencyGraph, path)
        features[self.featureSet.getId("len_edges_"+str(len(edges)))] = 1
        features[self.featureSet.getId("len")] = len(edges)
        self.buildPathRoleFeatures(path, edges, sentenceGraph, features)
        self.buildPathGrams(2, path, edges, sentenceGraph, features)
        self.buildEdgeCombinations(path, edges, sentenceGraph, features)
        #self.buildTerminusFeatures(path[0], "t1", sentenceGraph, features)
        #self.buildTerminusFeatures(path[-1], "t2", sentenceGraph, features)
        edgeList = []
        for i in range(1, len(path)):
            edgeList.extend(edges[i][i-1])
            edgeList.extend(edges[i-1][i])
        for edge in edgeList:
            self.buildPathEdgeFeatures(edge, sentenceGraph, features)
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
    
    def getWalks(self, pathTokens, pathEdges, position=1, walk=None):
        """
        A path is defined by a list of tokens. But since there can be more than one edge
        between the same two tokens, there are multiple ways of getting from the first
        token to the last token. This function returns all of these "walks", i.e. the combinations
        of edges that can be travelled to get from the first to the last token of the path.
        """
        allWalks = []
        if walk == None:
            walk = []
        
        edges = pathEdges[position-1][position] + pathEdges[position][position-1]
        for edge in edges:
            if position < len(pathTokens)-1:
                allWalks.extend(self.getWalks(pathTokens, pathEdges, position+1, walk + [edge]))
            else:
                allWalks.append(walk + [edge])
        return allWalks
    
    def buildPathGrams(self, length, pathTokens, pathEdges, sentenceGraph, features):
        walks = self.getWalks(pathTokens, pathEdges)
        dirGrams = []
        for walk in walks:
            dirGrams.append("")
        for i in range(len(pathTokens)-1): # len(pathTokens) == len(walk)
            for j in range(len(walks)):
                if walks[j][i][0] == pathTokens[i]:
                    dirGrams[j] += "F"
                else:
                    dirGrams[j] += "R"
                if i >= length-1:
                    styleGram = dirGrams[j][i-(length-1):i+1]
                    edgeGram = "depGram_" + styleGram
                    # Label tokens by their role in the xgram
                    for token in pathTokens[i-(length-1)+1:i+1]:
                        features[self.featureSet.getId("tok_"+styleGram+"_POS_"+token.attrib["POS"])] = 1
                        features[self.featureSet.getId("tok_"+styleGram+"_Txt_"+sentenceGraph.getTokenText(token))] = 1
                    # Label edges by their role in the xgram
                    position = 0
                    for edge in walks[j][i-(length-1):i+1]:
                        features[self.featureSet.getId("dep_"+styleGram+str(position)+"_"+edge[2].attrib["type"])] = 1
                        position += 1
    
    def buildPathRoleFeatures(self, pathTokens, pathEdges, sentenceGraph, features):
        #print len(pathTokens), len(pathEdges)
        features[self.featureSet.getId("tokTerm1POS_"+pathTokens[0].attrib["POS"])] = 1
        features[self.featureSet.getId("tokTerm1txt_"+sentenceGraph.getTokenText(pathTokens[0]))] = 1
        features[self.featureSet.getId("tokTerm2POS_"+pathTokens[-1].attrib["POS"])] = 1
        features[self.featureSet.getId("tokTerm2txt_"+sentenceGraph.getTokenText(pathTokens[-1]))] = 1
        
        return
#        for i in range(0,len(pathEdges)):
#            if pathEdges[i][1]:
#                features[self.featureSet.getId("depRight_"+pathEdges[i][0][2].attrib["type"])] = 1
#            else:
#                features[self.featureSet.getId("depLeft_"+pathEdges[i][0][2].attrib["type"])] = 1
        # Define roles for bigrams of two dependencies and their central token:
        #  -> = dependency, O = token
        #  ->O-> = Right
        #  <-O<- = Left
        #  <-O-> = Top
        #  ->O<- = Bottom
        for i in range(1,len(pathTokens)-1):
            if len(pathEdges[i-1][i]) > 0 and len(pathEdges[i][i+1]) > 0:
                for pathEdge in pathEdges[i-1][i]:
                    features[self.featureSet.getId("depRight1_"+pathEdge[2].attrib["type"])] = 1
                for pathEdge in pathEdges[i][i+1]:
                    features[self.featureSet.getId("depRight2_"+pathEdge[2].attrib["type"])] = 1
                features[self.featureSet.getId("tokRightPOS_"+pathTokens[i].attrib["POS"])] = 1
                features[self.featureSet.getId("tokRightTxt_"+sentenceGraph.getTokenText(pathTokens[i]))] = 1
            if len(pathEdges[i][i-1]) > 0 and len(pathEdges[i+1][i]) > 0:
                for pathEdge in pathEdges[i][i-1]:
                    features[self.featureSet.getId("depLeft1_"+pathEdge[2].attrib["type"])] = 1
                for pathEdge in pathEdges[i+1][i]:
                    features[self.featureSet.getId("depLeft2_"+pathEdge[2].attrib["type"])] = 1
                features[self.featureSet.getId("tokLeftPOS_"+pathTokens[i].attrib["POS"])] = 1
                features[self.featureSet.getId("tokLeftTxt_"+sentenceGraph.getTokenText(pathTokens[i]))] = 1
            if len(pathEdges[i][i-1]) > 0 and len(pathEdges[i][i+1]) > 0:
                for pathEdge in pathEdges[i][i-1]:
                    features[self.featureSet.getId("depTop1_"+pathEdge[2].attrib["type"])] = 1
                for pathEdge in pathEdges[i][i+1]:
                    features[self.featureSet.getId("depTop2_"+pathEdge[2].attrib["type"])] = 1
                features[self.featureSet.getId("tokTopPOS_"+pathTokens[i].attrib["POS"])] = 1
                features[self.featureSet.getId("tokTopTxt_"+sentenceGraph.getTokenText(pathTokens[i]))] = 1
            if len(pathEdges[i-1][i]) > 0 and len(pathEdges[i+1][i]) > 0:
                for pathEdge in pathEdges[i-1][i]:
                    features[self.featureSet.getId("depBottom1_"+pathEdge[2].attrib["type"])] = 1
                for pathEdge in pathEdges[i+1][i]:
                    features[self.featureSet.getId("depBottom2_"+pathEdge[2].attrib["type"])] = 1
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
    
    def buildEdgeCombinations(self, pathTokens, pathEdges, sentenceGraph, features):
        # Edges directed relative to the path
        for i in range(1,len(pathTokens)):
            for edge in pathEdges[i][i-1]:
                depType = edge[2].attrib["type"]
                features[self.featureSet.getId("dep_"+depType+">")] = 1
            for edge in pathEdges[i-1][i]:
                depType = edge[2].attrib["type"]
                features[self.featureSet.getId("dep_<"+depType)] = 1

        # Internal tokens
        for i in range(1,len(pathTokens)-1):
            features[self.featureSet.getId("internalPOS_"+pathTokens[i].attrib["POS"])]=1
            features[self.featureSet.getId("internalTxt_"+sentenceGraph.getTokenText(pathTokens[i]))]=1
        # Internal dependencies
        for i in range(2,len(pathTokens)-1):
            for edge in pathEdges[i][i-1]:
                features[self.featureSet.getId("internalDep_"+edge[2].attrib["type"])] = 1
            for edge in pathEdges[i-1][i]:
                features[self.featureSet.getId("internalDep_"+edge[2].attrib["type"])] = 1
            
#        if edges[0][1]:
#            features[self.featureSet.getId("internalPOS_"+edges[0][0][0].attrib["POS"])]=1
#            features[self.featureSet.getId("internalTxt_"+sentenceGraph.getTokenText(edges[0][0][0]))]=1
#        else:
#            features[self.featureSet.getId("internalPOS_"+edges[0][0][1].attrib["POS"])]=1
#            features[self.featureSet.getId("internalTxt_"+sentenceGraph.getTokenText(edges[0][0][1]))]=1
#        if edges[-1][1]:
#            features[self.featureSet.getId("internalPOS_"+edges[-1][0][1].attrib["POS"])]=1
#            features[self.featureSet.getId("internalTxt_"+sentenceGraph.getTokenText(edges[-1][0][1]))]=1
#        else:
#            features[self.featureSet.getId("internalPOS_"+edges[-1][0][0].attrib["POS"])]=1
#            features[self.featureSet.getId("internalTxt_"+sentenceGraph.getTokenText(edges[-1][0][0]))]=1
#        for i in range(1,len(edges)-1):
#            features[self.featureSet.getId("internalPOS_"+edges[i][0][0].attrib["POS"])]=1
#            features[self.featureSet.getId("internalTxt_"+sentenceGraph.getTokenText(edges[i][0][0]))]=1
#            features[self.featureSet.getId("internalPOS_"+edges[i][0][1].attrib["POS"])]=1
#            features[self.featureSet.getId("internalTxt_"+sentenceGraph.getTokenText(edges[i][0][1]))]=1
#            features[self.featureSet.getId("internalDep_"+edges[i][0][2].attrib["type"])]=1
        
        # Edge bigrams
        for i in range(1,len(pathTokens)-1):
            edgesForward1 = pathEdges[i][i-1]
            edgesReverse1 = pathEdges[i-1][i]
            edgesForward2 = pathEdges[i][i+1]
            edgesReverse2 = pathEdges[i+1][i]
            for e1 in edgesForward1:
                for e2 in edgesForward2:
                    features[self.featureSet.getId("dep_"+e1[2].attrib["type"]+">"+e2[2].attrib["type"]+">")] = 1
            for e1 in edgesReverse1:
                for e2 in edgesReverse2:
                    features[self.featureSet.getId("dep_"+e1[2].attrib["type"]+"<"+e2[2].attrib["type"]+"<")] = 1
            for e1 in edgesForward1:
                for e2 in edgesReverse2:
                    features[self.featureSet.getId("dep_"+e1[2].attrib["type"]+">"+e2[2].attrib["type"]+"<")] = 1
            for e1 in edgesReverse1:
                for e2 in edgesForward2:
                    features[self.featureSet.getId("dep_"+e1[2].attrib["type"]+"<"+e2[2].attrib["type"]+">")] = 1
                
#        for i in range(1,len(edges)):
#            type1 = edges[i-1][0][2].attrib["type"]
#            type2 = edges[i][0][2].attrib["type"]
#            if edges[i-1][1] and edges[i][1]:
#                features[self.featureSet.getId("dep_"+type1+">"+type2+">")] = 1
#            elif edges[i-1][1] and edges[i][0]:
#                features[self.featureSet.getId("dep_"+type1+">"+type2+"<")] = 1
#            elif edges[i-1][0] and edges[i][0]:
#                features[self.featureSet.getId("dep_"+type1+"<"+type2+"<")] = 1
#            elif edges[i-1][0] and edges[i][1]:
#                features[self.featureSet.getId("dep_"+type1+"<"+type2+">")] = 1
   
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