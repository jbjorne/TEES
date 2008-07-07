import networkx as NX
import Range

class SentenceGraph:
    def __init__(self, tokenElements, dependencyElements):
        self.tokens = tokenElements
        self.dependencies = dependencyElements
        self.dependencyGraph = NX.XDiGraph()
        self.interactions = None
        self.entities = None
        self.interactionGraph = None
        
        self.tokensById = {}
        for token in self.tokens:
            self.tokensById[token.attrib["id"]] = token
            self.dependencyGraph.add_node(token)
        #self.dependenciesById = {}
        for dependency in self.dependencies:
            self.dependencyGraph.add_edge(self.tokensById[dependency.attrib["t1"]],\
                                          self.tokensById[dependency.attrib["t2"]],\
                                          dependency)
            #self.dependenciesById[dependency.attrib["id"]] = dependency
    
    def mapInteractions(self, entityElements, interactionElements):
        self.interactions = interactionElements
        self.entities = entityElements
        self.interactionGraph = NX.XDiGraph()
        
        for token in self.tokens:
            self.interactionGraph.add_node(token)
        
        self.entitiesById = {}
        for entity in self.entities:
            self.entitiesById[entity.attrib["id"]] = entity
        for interaction in self.interactions:
            token1 = self.mapEntity(self.entitiesById[interaction.attrib["e1"]])
            token2 = self.mapEntity(self.entitiesById[interaction.attrib["e2"]])
            self.interactionGraph.add_edge(token1, token2, interaction)
    
    def mapEntity(self, entityElement):
        headOffset = Range.charOffsetToSingleTuple(entityElement.attrib["headOffset"])
        headTokens = []
        for token in self.tokens:
            tokenOffset = Range.charOffsetToSingleTuple(token.attrib["charOffset"])
            if Range.overlap(headOffset,tokenOffset):
                headTokens.append(token)
        #assert(len(headTokens)==1) # Terrible hack, but should work for now
        if len(headTokens)==1:
            return headTokens[0]
        else:
            token = self.findHeadToken(headTokens)
            print "Selected head:", token.attrib["id"], token.attrib["text"]
            return token
    
    def findHeadToken(self, candidateTokens):
        # Remove tokens that clearly can't be head and are probably produced by hyphen-splitter
        for token in candidateTokens[:]:
            tokenText = token.attrib["text"]
            if tokenText == "\\" or tokenText == "/" or tokenText == "-":
                if len(candidateTokens) > 1:
                    candidateTokens.remove(token)
        if len(candidateTokens) == 1:
            return candidateTokens[0]
        
        # Remove tokens that are linked to the probable head with certain link-types
        tokenScores = len(candidateTokens) * [0]
        depTypesToRemove = ["nn", "det", "hyphen", "num", "amod", "nmod"]
        edges = self.dependencyGraph.edges()
        for edge in edges:
            if edge[0] in candidateTokens and edge[1] in candidateTokens:
                if edge[2].attrib["type"] in depTypesToRemove:
                    tokenScores[candidateTokens.index(edge[1])] -= 1
        
        # Return head token based on score
        highestScore = -9999999
        for i in range(len(candidateTokens)):
            if tokenScores[i] > highestScore:
                highestScore = tokenScores[i]
        for i in range(len(candidateTokens)):
            if tokenScores[i] == highestScore:
                return candidateTokens[i]