from FeatureBuilder import FeatureBuilder

class NodalidaFeatureBuilder(FeatureBuilder):
    def __init__(self, featureSet):
        FeatureBuilder.__init__(self, featureSet)
    
    def buildShortestPaths(self, graph, tokenPath, position=0, newPath=None):
        if newPath == None:
            assert(position == 0)
            newPath = [tokenPath[0]]
        else:
            newPath = newPath + [tokenPath[position]]
        
        if position == len(tokenPath) - 1:
            return [newPath]
        forwardEdges = []
        if graph.has_edge(tokenPath[position],tokenPath[position+1]):
            forwardEdges.extend(graph.get_edge(tokenPath[position],tokenPath[position+1]))
        reverseEdges = []
        if graph.has_edge(tokenPath[position+1],tokenPath[position]):
            reverseEdges.extend(graph.get_edge(tokenPath[position+1],tokenPath[position]))
        newPaths = []
        for reverseEdge in reverseEdges:
            newPaths.extend( self.buildShortestPaths(graph, tokenPath, position+1, newPath + [(reverseEdge,"reverse")]) )
        for forwardEdge in forwardEdges:
            newPaths.extend( self.buildShortestPaths(graph, tokenPath, position+1, newPath + [(forwardEdge,"forward")]) )
        return newPaths
    
    def buildTokenGramFeatures(self, tokenPath, sentenceGraph):
        txtGrams = [""]
        annTypeGrams = [""]
        posGrams = [""]
        for token in tokenPath:
            featureList = self.getTokenFeatures(token, sentenceGraph)
            for feature in featureList:
                if feature.find("txt_") != -1:
                    newGrams = []
                    for gram in txtGrams:
                        newGrams.append(gram + feature)
                    txtGrams = newGrams
                elif feature.find("POS_") != -1:
                    newGrams = []
                    for gram in posGrams:
                        newGrams.append(gram + feature)
                    posGrams = newGrams
                elif feature.find("annType_") != -1:
                    newGrams = []
                    for gram in annTypeGrams:
                        newGrams.append(gram + feature)
                    annTypeGrams = newGrams
        for gram in txtGrams + annTypeGrams + posGrams:
            if gram != "":
                self.setFeature(gram, 1)
    
    def buildEdgeGramFeatures(self, edgePath):
        string = ""
        print edgePath
        for edge in edgePath:
            string += edge[0].attrib["type"] + "-" + edge[1]
        self.setFeature(string, 1)
    
    def buildNGrams(self, paths, sentenceGraph, n=3):
        for path in paths:
            assert(len(path)%2==1)
            tokenPhase = True
            for i in range(len(path)):
                # Token n-grams
                if tokenPhase:
                    tokenGram = []
                    for j in range(i, max(-1,i-n*2), -2):
                        tokenGram = [path[j]] + tokenGram
                        self.buildTokenGramFeatures(tokenGram, sentenceGraph)
                # Dependency n-grams
                else:
                    edgeGram = []
                    for j in range(i, max(0,i-n*2), -2):
                        edgeGram = [path[j]] + edgeGram
                        self.buildEdgeGramFeatures(tokenGram)
                tokenPhase = not tokenPhase