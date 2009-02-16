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
    if corpusFilename.rsplit(".",1)[-1] == "gz":
        import gzip
        corpusTree = ET.parse(gzip.open(corpusFilename))
    else:
        corpusTree = ET.parse(corpusFilename)
    corpusRoot = corpusTree.getroot()
    corpusElements = CorpusElements(corpusRoot, parse, tokenization)
    print >> sys.stderr, str(len(corpusElements.documentsById)) + " documents, " + str(len(corpusElements.sentencesById)) + " sentences"
    # Make sentence graphs
    duplicateInteractionEdgesRemoved = 0
    sentences = []
    counter = ProgressCounter(len(corpusElements.sentences), "Make sentence graphs")
    for sentence in corpusElements.sentences[:]:
        counter.update(1, "Making sentence graphs ("+sentence.sentence.attrib["id"]+"): ")
        if len(sentence.tokens) == 0:
            corpusElements.sentences.remove(sentence)
            continue
        for pair in sentence.pairs:
            if pair.attrib["interaction"] == "True":
                sentence.interactions.append(pair)
                if not pair.attrib.has_key("type"):
                    pair.attrib["type"] = "undefined"
        graph = SentenceGraph(sentence.sentence, sentence.tokens, sentence.dependencies)
        graph.mapInteractions(sentence.entities, sentence.interactions)
        duplicateInteractionEdgesRemoved += graph.duplicateInteractionEdgesRemoved
        sentence.sentenceGraph = graph
    print >> sys.stderr, "Removed", duplicateInteractionEdgesRemoved, "duplicate interaction edges"
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
        self.duplicateInteractionEdgesRemoved = 0
        self.tokenHeadScores = None
        
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
    
    def getInteractions(self, entity1, entity2):
        rv = []
        for interaction in self.interactions:
            if interaction.attrib["e1"] == entity1.attrib["id"] and interaction.attrib["e2"] == entity2.attrib["id"]:
                rv.append(interaction)
        return rv
    
    def mapInteractions(self, entityElements, interactionElements, verbose=False):
        self.interactions = interactionElements
        self.entities = entityElements
        for entity in self.entities[:]:
            if entity.attrib["charOffset"] == "":
                self.entities.remove(entity)
        self.interactionGraph = NX.XDiGraph(multiedges = multiedges)
        self.entitiesByToken = {}
        
        for token in self.tokens:
            self.interactionGraph.add_node(token)
        
        self.entitiesById = {}
        self.entityHeadTokenByEntity = {}
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
            self.entityHeadTokenByEntity[entity] = self.mapEntity(entity, verbose)
        self.__markNamedEntities()
        
        for interaction in self.interactions:
            if not self.entitiesById.has_key(interaction.attrib["e1"]):
                continue
            if not self.entitiesById.has_key(interaction.attrib["e2"]):
                continue
            token1 = self.entityHeadTokenByEntity[self.entitiesById[interaction.attrib["e1"]]]
            token2 = self.entityHeadTokenByEntity[self.entitiesById[interaction.attrib["e2"]]]
            
            found = False
            if multiedges:
                edges = self.interactionGraph.get_edge(token1, token2)
                for edge in edges:
                    if edge.attrib["type"] == interaction.attrib["type"]:
                        found = True
                        break
            if not found:
                self.interactionGraph.add_edge(token1, token2, interaction)
            else:
                self.duplicateInteractionEdgesRemoved += 1
    
    def mapEntity(self, entityElement, verbose=False):
        headOffset = None
        if entityElement.attrib.has_key("headOffset"):
            headOffset = Range.charOffsetToSingleTuple(entityElement.attrib["headOffset"])
        if entityElement.attrib["charOffset"] != "":
            charOffsets = Range.charOffsetToTuples(entityElement.attrib["charOffset"])
        else:
            charOffsets = []
        headTokens = []
        for token in self.tokens:
            tokenOffset = Range.charOffsetToSingleTuple(token.attrib["charOffset"])
            if headOffset != None:
                if Range.overlap(headOffset,tokenOffset):
                    headTokens.append(token)
            else:
                for offset in charOffsets:
                    if Range.overlap(offset,tokenOffset):
                        headTokens.append(token)
        #assert(len(headTokens)==1) # Terrible hack, but should work for now
        if len(headTokens)==1:
            token = headTokens[0]
        else:
            token = self.findHeadToken(headTokens)
            if verbose:
                print >> sys.stderr, "Selected head:", token.attrib["id"], token.attrib["text"]
        if token != None:
            if not entityElement.attrib.has_key("headOffset"):
                entityElement.attrib["headOffset"] = token.attrib["charOffset"]
            if not self.entitiesByToken.has_key(token):
                self.entitiesByToken[token] = []
            self.entitiesByToken[token].append(entityElement)
        return token
    
#    def findHeadToken(self, candidateTokens):
#        # Remove tokens that clearly can't be head and are probably produced by hyphen-splitter
#        for token in candidateTokens[:]:
#            tokenText = token.attrib["text"]
#            if tokenText == "\\" or tokenText == "/" or tokenText == "-":
#                if len(candidateTokens) > 1:
#                    candidateTokens.remove(token)
#        if len(candidateTokens) == 1:
#            return candidateTokens[0]
#        
#        # Remove tokens that are linked to the probable head with certain link-types
#        tokenScores = len(candidateTokens) * [0]
#        depTypesToRemove = ["nn", "det", "hyphen", "num", "amod", "nmod"]
#        edges = self.dependencyGraph.edges()
#        for edge in edges:
#            if edge[0] in candidateTokens and edge[1] in candidateTokens:
#                if edge[2].attrib["type"] in depTypesToRemove:
#                    tokenScores[candidateTokens.index(edge[1])] -= 1
#        
#        # Return head token based on score
#        highestScore = -9999999
#        for i in range(len(candidateTokens)):
#            if tokenScores[i] > highestScore:
#                highestScore = tokenScores[i]
#        for i in range(len(candidateTokens)):
#            if tokenScores[i] == highestScore:
#                return candidateTokens[i]
#        return None

    def findHeadToken(self, candidateTokens):        
        tokenHeadScores = self.getTokenHeadScores()
        
        #if debug:
        #    print "Tokens:", candidateTokenIds
        #    print "Scores:", tokenScores
        
        if len(candidateTokens) == 0:
            return None
        
        highestScore = -9999999
        bestTokens = []
        for token in candidateTokens:
            if tokenHeadScores[token] > highestScore:
                highestScore = tokenHeadScores[token]
        for token in candidateTokens:
            if tokenHeadScores[token] == highestScore:
                bestTokens.append(token)
#        if debug:
#            print "tokens:"
#            for i in range(len(candidateTokenIds)):
#                print "[", candidateTokenIds[i], self.tokensById[candidateTokenIds[i]].text, tokenHeadScores[candidateTokenIds[i]], "]"
        return bestTokens[-1]
    
#    def setTokenHeadScore(self, token, visited, dependencies):
#        if visited == None:
#            visited = []
#        visited.append(token.attrib["id"])
#        for dependency in dependencies:
#            if dep.attrib["t2"] == token.attrib["id"]:
#                if self.tokenHeadScores[dep.attrib["t1"]] <= self.tokenHeadScores[dep.attrib["t2"]]:
#                    self.tokenHeadScores[dep.attrib["t1"]] = self.tokenHeadScores[dep.attrib["t2"]] + 1
#                if dep.attrib["t1"] not in visited:
#                    setTokenHeadScore(self, self.tokensById[dep.attrib["t1"]], visited, dependencies)

    def getTokenHeadScores(self):
        if self.tokenHeadScores != None:
            return self.tokenHeadScores
        else:
            self.tokenHeadScores = {}
        depTypesToRemove = ["prep", "nn", "det", "hyphen", "num", "amod", "nmod", "appos", "measure", "dep", "partmod"]
        depTypesToRemoveReverse = ["A/AN"]
        for token in self.tokens:
            self.tokenHeadScores[token] = 0
            for dependency in self.dependencies:
                if dependency.attrib["t1"] == token.attrib["id"] or dependency.attrib["t2"] == token.attrib["id"]:
                    self.tokenHeadScores[token] = 1
                    break               
        
        # Give a low score for tokens that clearly can't be head and are probably produced by hyphen-splitter
        for token in self.tokens:
            tokenText = token.attrib["text"]
            if tokenText == "\\" or tokenText == "/" or tokenText == "-":
                self.tokenHeadScores[token] = -1
        
        modifiedScores = True
        while modifiedScores == True:
            modifiedScores = False
            for token1 in self.tokens:
                for token2 in self.tokens:
                    for dep in self.dependencies:
                        if dep.attrib["t1"] == token1.attrib["id"] and dep.attrib["t2"] == token2.attrib["id"] and (dep.attrib["type"] in depTypesToRemove):
                            #tokenScores[i] -= 1
                            if self.tokenHeadScores[token1] <= self.tokenHeadScores[token2]:
                                self.tokenHeadScores[token1] = self.tokenHeadScores[token2] + 1
                                modifiedScores = True
#                        elif dep.attrib["t1"] == tokenI.attrib["id"] and dep.attrib["t2"] == tokenJ.attrib["id"] and (dep.attrib["type"] in depTypesToRemoveReverse):
#                            #tokenScores[i] -= 1
#                            if self.tokenHeadScores[tokenJ] <= self.tokenHeadScores[tokenI]:
#                                self.tokenHeadScores[tokenJ] = self.tokenHeadScores[tokenI] + 1
#                                modifiedScores = True
        #print self.tokenHeadScores
        return self.tokenHeadScores

    def __markNamedEntities(self):
        self.tokenIsName = {}
        self.tokenIsEntity = {}
        self.tokenIsEntityHead = {}
        for token in self.tokens:
            self.tokenIsName[token] = False
            self.tokenIsEntity[token] = False
            self.tokenIsEntityHead[token] = []
        for entity in self.entities:
            entityOffsets = Range.charOffsetToTuples(entity.attrib["charOffset"])
            entityHeadOffset = Range.charOffsetToSingleTuple(entity.attrib["headOffset"])
            for token in self.tokens:
                tokenOffset = Range.charOffsetToSingleTuple(token.attrib["charOffset"])
                for entityOffset in entityOffsets:
                    if Range.overlap(entityOffset, tokenOffset):
                        self.tokenIsEntity[token] = True
                        if entity.attrib.has_key("isName"):
                            if entity.attrib["isName"] == "True":
                                self.tokenIsName[token] = True
                        else:
                            entity.attrib["isName"] = "True"
                            self.tokenIsName[token] = True
                if Range.overlap(entityHeadOffset, tokenOffset):
                    self.tokenIsEntityHead[token].append(entity)
                                                          
    def getTokenText(self, token):
        if self.tokenIsName[token]:
            return "NAMED_ENT"
        else:
            return token.get("text") #.lower()
