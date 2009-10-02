import networkx as NX
import Range
import types

multiedges = True

def loadCorpus(corpus, parse, tokenization=None, removeNameInfo=False):
    """
    Load an entire corpus through CorpusElements and add SentenceGraph-objects
    to its SentenceElements-objects.
    """
    import cElementTreeUtils as ETUtils
    import sys
    sys.path.append("..")
    from Utils.ProgressCounter import ProgressCounter
    from InteractionXML.CorpusElements import CorpusElements
    
    # Corpus may be in file or not
    if type(corpus) == types.StringType:
        print >> sys.stderr, "Loading corpus file", corpus
    corpusTree = ETUtils.ETFromObj(corpus)
    corpusRoot = corpusTree.getroot()
    # Use CorpusElements-class to access xml-tree
    corpusElements = CorpusElements(corpusRoot, parse, tokenization, tree=corpusTree, removeNameInfo=removeNameInfo)
    print >> sys.stderr, str(len(corpusElements.documentsById)) + " documents, " + str(len(corpusElements.sentencesById)) + " sentences"
    # Make sentence graphs
    duplicateInteractionEdgesRemoved = 0
    sentences = []
    counter = ProgressCounter(len(corpusElements.sentences), "Make sentence graphs")
    for sentence in corpusElements.sentences[:]:
        counter.update(1, "Making sentence graphs ("+sentence.sentence.attrib["id"]+"): ")
        if len(sentence.tokens) == 0: # No tokens, no sentence
            corpusElements.sentences.remove(sentence)
            continue
        for pair in sentence.pairs:
            # gif-xml defines to closely related element types, interactions and
            # pairs. Pairs are like interactions, but they can also be negative (if
            # interaction-attribute == False). Sometimes pair-elements have been
            # (incorrectly) used without this attribute. To work around these issues
            # we take all pair-elements that define interaction and add them to
            # the interaction-element list.
            isInteraction = pair.get("interaction")
            if isInteraction == "True" or isInteraction == None:
                sentence.interactions.append(pair) # add to interaction-elements
                if not pair.attrib.has_key("type"): # type-attribute must be explicitly defined
                    pair.attrib["type"] = "undefined"
        # Construct the basic SentenceGraph (only syntactic information)
        graph = SentenceGraph(sentence.sentence, sentence.tokens, sentence.dependencies)
        # Add semantic information, i.e. the interactions
        graph.mapInteractions(sentence.entities, sentence.interactions)
        graph.interSentenceInteractions = sentence.interSentenceInteractions
        duplicateInteractionEdgesRemoved += graph.duplicateInteractionEdgesRemoved
        sentence.sentenceGraph = graph
    print >> sys.stderr, "Removed", duplicateInteractionEdgesRemoved, "duplicate interaction edges"
    return corpusElements

class SentenceGraph:
    """
    The main purpose of SentenceGraph is to connect the syntactic dependency
    parse (a graph where dependencies are edges and tokens are nodes) to the
    semantic interactions (which form a graph where interactions are edges
    and entities are nodes). Additionally, SentenceGraph provides several
    dictionaries that e.g. map element ids to their corresponding elements.
    """
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
            self.tokensById[token.get("id")] = token
            self.dependencyGraph.add_node(token)
        # Build the dependency graph using token-elements as nodes and dependency-elements
        # as edge data
        for dependency in self.dependencies:
            self.dependencyGraph.add_edge(self.tokensById[dependency.attrib["t1"]],\
                                          self.tokensById[dependency.attrib["t2"]],\
                                          dependency)
    
    def getSentenceId(self):
        return self.sentenceElement.get("id")
    
    def getInteractions(self, entity1, entity2):
        """
        Return a list of interaction-elements which represent directed
        interactions from entity1 to entity2.
        """
        rv = []
        for interaction in self.interactions:
            if interaction.attrib["e1"] == entity1.attrib["id"] and interaction.attrib["e2"] == entity2.attrib["id"]:
                rv.append(interaction)
        return rv
    
    def mapInteractions(self, entityElements, interactionElements, verbose=False):
        """
        Maps the semantic interactions to the syntactic graph.
        
        Syntactic dependencies are defined between tokens. Semantic edges (interactions)
        are defined between annotated entities. To utilize the correlation of the dependency
        parse with the semantic interactions, the graphs must be aligned by mapping the
        interaction graph's nodes (entities) to the syntactic graph's nodes (tokens). This
        is done by determining the head tokens of the entities.
        """
        self.interactions = interactionElements
        self.entities = entityElements
        # Entities that have no text binding can not be mapped and are therefore removed
        for entity in self.entities[:]:
            if entity.attrib["charOffset"] == "":
                self.entities.remove(entity)
        self.interactionGraph = NX.XDiGraph(multiedges = multiedges)
        for token in self.tokens:
            self.interactionGraph.add_node(token)
        
        self.entitiesByToken = {} # a mapping for fast access
        self.entitiesById = {}
        self.entityHeadTokenByEntity = {}
        for entity in self.entities:
            self.entitiesById[entity.attrib["id"]] = entity
            self.entityHeadTokenByEntity[entity] = self.mapEntity(entity, verbose)
        self._markNamedEntities()
        
        for interaction in self.interactions:
            if not self.entitiesById.has_key(interaction.attrib["e1"]):
                continue # e1 is outside of this sentence
            if not self.entitiesById.has_key(interaction.attrib["e2"]):
                continue # e2 is outside of this sentence
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
        """
        """
        headOffset = None
        if entityElement.attrib.has_key("headOffset"):
            headOffset = Range.charOffsetToSingleTuple(entityElement.attrib["headOffset"])
        if entityElement.attrib["charOffset"] != "":
            charOffsets = Range.charOffsetToTuples(entityElement.attrib["charOffset"])
        else:
            charOffsets = []
        # Each entity can consist of multiple syntactic tokens, covered by its
        # charOffset-range. One of these must be chosen as the head token.
        headTokens = [] # potential head tokens
        for token in self.tokens:
            #print token.attrib["id"], token.attrib["charOffset"]
            tokenOffset = Range.charOffsetToSingleTuple(token.attrib["charOffset"])
            if headOffset != None:
                # A head token can already be defined in the headOffset-attribute.
                # However, depending on the tokenization, even this range may
                # contain multiple tokens. Still, it can always be assumed that
                # if headOffset is defined, the corret head token is in this range.
                if Range.overlap(headOffset,tokenOffset):
                    headTokens.append(token)
            else:
                for offset in charOffsets:
                    if Range.overlap(offset,tokenOffset):
                        headTokens.append(token)
        if len(headTokens)==1: # An unambiguous head token was found
            token = headTokens[0]
        else: # One head token must be chosen from the candidates
            token = self.findHeadToken(headTokens)
            if verbose:
                print >> sys.stderr, "Selected head:", token.attrib["id"], token.attrib["text"]
        assert token != None, entityElement.get("id")
        if token != None:
            # The ElementTree entity-element is modified by setting the headOffset attribute
            if not entityElement.attrib.has_key("headOffset"):
                entityElement.attrib["headOffset"] = token.attrib["charOffset"]
            if not self.entitiesByToken.has_key(token):
                self.entitiesByToken[token] = []
            self.entitiesByToken[token].append(entityElement)
        return token

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

    def getTokenHeadScores(self):
        """
        A head token is chosen using a heuristic that prefers tokens closer to the
        root of the dependency parse. In a list of candidate tokens, the one with
        the highest score is the head token. The return value of this method
        is a dictionary that maps token elements to their scores.
        """
        # Token head scores are cached the first time this function is called
        if self.tokenHeadScores != None:
            return self.tokenHeadScores
        else:
            self.tokenHeadScores = {}
        
        # Give all tokens initial scores
        for token in self.tokens:
            self.tokenHeadScores[token] = 0 # initialize score as zero (unconnected token)
            for dependency in self.dependencies:
                if dependency.attrib["t1"] == token.attrib["id"] or dependency.attrib["t2"] == token.attrib["id"]:
                    self.tokenHeadScores[token] = 1 # token is connected by a dependency
                    break               
        
        # Give a low score for tokens that clearly can't be head and are probably produced by hyphen-splitter
        for token in self.tokens:
            tokenText = token.attrib["text"]
            if tokenText == "\\" or tokenText == "/" or tokenText == "-":
                self.tokenHeadScores[token] = -1
        
        # Loop over all dependencies and increase the scores of all governor tokens
        # until each governor token has a higher score than its dependent token.
        # Some dependencies might form a loop so a list is used to define those
        # dependency types used in determining head scores.
        depTypesToInclude = ["prep", "nn", "det", "hyphen", "num", "amod", "nmod", "appos", "measure", "dep", "partmod"]
        #depTypesToRemoveReverse = ["A/AN"]
        modifiedScores = True
        while modifiedScores == True: # loop until the scores no longer change
            modifiedScores = False
            for token1 in self.tokens:
                for token2 in self.tokens: # for each combination of tokens...
                    for dep in self.dependencies: # ... check each dependency
                        if dep.attrib["t1"] == token1.attrib["id"] and dep.attrib["t2"] == token2.attrib["id"] and (dep.attrib["type"] in depTypesToInclude):
                            # The governor token of the dependency must have a higher score
                            # than the dependent token.
                            if self.tokenHeadScores[token1] <= self.tokenHeadScores[token2]:
                                self.tokenHeadScores[token1] = self.tokenHeadScores[token2] + 1
                                modifiedScores = True
#                        elif dep.attrib["t1"] == tokenI.attrib["id"] and dep.attrib["t2"] == tokenJ.attrib["id"] and (dep.attrib["type"] in depTypesToRemoveReverse):
#                            #tokenScores[i] -= 1
#                            if self.tokenHeadScores[tokenJ] <= self.tokenHeadScores[tokenI]:
#                                self.tokenHeadScores[tokenJ] = self.tokenHeadScores[tokenI] + 1
#                                modifiedScores = True
        return self.tokenHeadScores

    def _markNamedEntities(self):
        """
        This method is used to define which tokens belong to _named_ entities.
        Named entities are sometimes masked when testing learning of interactions, to
        prevent the system making a trivial decision based on commonly interacting names.
        """
        self.tokenIsName = {}
        self.tokenIsEntity = {}
        self.tokenIsEntityHead = {}
        # Initialize the dictionaries
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
        """
        Returns the text of a token, and masks it if the token is the head token
        of a named entity.
        """
        if self.tokenIsName[token]:
            return "NAMED_ENT"
        else:
            return token.get("text")
