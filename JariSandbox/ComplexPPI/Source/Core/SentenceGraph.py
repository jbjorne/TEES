import networkx as NX
import Range

multiedges = True

def loadCorpus(corpusFilename, parse, tokenization=None):
    try:
        import xml.etree.cElementTree as ET
    except ImportError:
        import cElementTree as ET
    import sys
    sys.path.append("..")
    from Utils.ProgressCounter import ProgressCounter
    from InteractionXML.CorpusElements import CorpusElements
    
    print >> sys.stderr, "Loading corpus file", corpusFilename
    corpusTree = ET.parse(corpusFilename)
    corpusRoot = corpusTree.getroot()
    corpusElements = CorpusElements(corpusRoot, parse, tokenization)
    print >> sys.stderr, str(len(corpusElements.documentsById)) + " documents, " + str(len(corpusElements.sentencesById)) + " sentences"
    # Make sentence graphs
    sentences = []
    counter = ProgressCounter(len(corpusElements.sentences), "Make sentence graphs")
    for sentence in corpusElements.sentences:
        counter.update(1, "Making sentence graphs ("+sentence.sentence.attrib["id"]+"): ")
        graph = SentenceGraph(sentence.sentence, sentence.tokens, sentence.dependencies)
        graph.mapInteractions(sentence.entities, sentence.interactions)
        sentence.sentenceGraph = graph
    return corpusElements

class SentenceGraph:
    def __init__(self, sentenceElement, tokenElements, dependencyElements):
        self.sentenceElement = sentenceElement
        self.tokens = tokenElements
        self.dependencies = dependencyElements
        self.dependencyGraph = NX.XDiGraph(multiedges = multiedges)
        self.interactions = None
        self.entities = None
        self.interactionGraph = None
        
        self.tokensById = {}
        for token in self.tokens:
            self.tokensById[token.attrib["id"]] = token
            self.dependencyGraph.add_node(token)
        #self.dependenciesById = {}
        for dependency in self.dependencies:
            #if dependency.attrib["type"] == "conj_and":
            #    continue
            self.dependencyGraph.add_edge(self.tokensById[dependency.attrib["t1"]],\
                                          self.tokensById[dependency.attrib["t2"]],\
                                          dependency)
            #self.dependenciesById[dependency.attrib["id"]] = dependency
    
    def getSentenceId(self):
        return self.sentenceElement.attrib["id"]
        
    def mapInteractions(self, entityElements, interactionElements, verbose=False):
        self.interactions = interactionElements
        self.entities = entityElements
        self.interactionGraph = NX.XDiGraph(multiedges = multiedges)
        self.entitiesByToken = {}
        
        self.__markNamedEntities()
        
        for token in self.tokens:
            self.interactionGraph.add_node(token)
        
        self.entitiesById = {}
        entityHeadTokenByEntity = {}
#        for entity in self.entities[:]:
#            entityIsPartOfInteractionGraph = False
#            for interaction in self.interactions:
#                if interaction.attrib["e1"] == entity.attrib["id"] or interaction.attrib["e2"] == entity.attrib["id"]:
#                    entityIsPartOfInteractionGraph = True
#                    break
#            if entityIsPartOfInteractionGraph:
#                self.entitiesById[entity.attrib["id"]] = entity
#                entityHeadTokenByEntity[entity] = self.mapEntity(entity, verbose)
#            else:
#                self.entities.remove(entity)
        for entity in self.entities:
            self.entitiesById[entity.attrib["id"]] = entity
            entityHeadTokenByEntity[entity] = self.mapEntity(entity, verbose)
        for interaction in self.interactions:
            token1 = entityHeadTokenByEntity[self.entitiesById[interaction.attrib["e1"]]]
            token2 = entityHeadTokenByEntity[self.entitiesById[interaction.attrib["e2"]]]
            
            found = False
            if multiedges:
                edges = self.interactionGraph.get_edge(token1, token2)
                for edge in edges:
                    if edge.attrib["type"] == interaction.attrib["type"]:
                        found = True
                        break
            if not found:
                self.interactionGraph.add_edge(token1, token2, interaction)
    
    def mapEntity(self, entityElement, verbose=False):
        headOffset = Range.charOffsetToSingleTuple(entityElement.attrib["headOffset"])
        headTokens = []
        for token in self.tokens:
            tokenOffset = Range.charOffsetToSingleTuple(token.attrib["charOffset"])
            if Range.overlap(headOffset,tokenOffset):
                headTokens.append(token)
        #assert(len(headTokens)==1) # Terrible hack, but should work for now
        if len(headTokens)==1:
            token = headTokens[0]
        else:
            token = self.findHeadToken(headTokens)
            if verbose:
                print >> sys.stderr, "Selected head:", token.attrib["id"], token.attrib["text"]
        if not self.entitiesByToken.has_key(token):
            self.entitiesByToken[token] = []
        self.entitiesByToken[token].append(entityElement)
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

    def __markNamedEntities(self):
        self.tokenIsName = {}
        self.tokenIsEntity = {}
        self.tokenIsEntityHead = {}
        for token in self.tokens:
            self.tokenIsName[token] = False
            self.tokenIsEntity[token] = False
            self.tokenIsEntityHead[token] = None
        for entity in self.entities:
            entityOffsets = Range.charOffsetToTuples(entity.attrib["charOffset"])
            entityHeadOffset = Range.charOffsetToSingleTuple(entity.attrib["headOffset"])
            for token in self.tokens:
                tokenOffset = Range.charOffsetToSingleTuple(token.attrib["charOffset"])
                for entityOffset in entityOffsets:
                    if Range.overlap(entityOffset, tokenOffset):
                        self.tokenIsEntity[token] = True
                        if entity.attrib["isName"] == "True":
                            self.tokenIsName[token] = True
                if Range.overlap(entityHeadOffset, tokenOffset):
                    self.tokenIsEntityHead[token] = entity

    def getTokenText(self, token):
        if self.tokenIsName[token]:
            return "NAMED_ENT"
        else:
            return token.attrib["text"]
