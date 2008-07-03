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
        assert(len(headTokens)==1) # Terrible hack, but should work for now
        return headTokens[0]
    
    def findHeadToken(self, charOffsets):
        pass
        # Kopioi GeniaParseGraphista