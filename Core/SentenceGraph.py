"""
Main class for representing a sentence
"""
__version__ = "$Revision: 1.40 $"

#import Graph.networkx_v10rc1 as NX10 # import networkx as NX
from SimpleGraph import Graph
import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/..")
import Utils.Range as Range
import types
import copy

#multiedges = True

def loadCorpus(corpus, parse, tokenization=None, removeNameInfo=False, removeIntersentenceInteractionsFromCorpusElements=True):
    """
    Load an entire corpus through CorpusElements and add SentenceGraph-objects
    to its SentenceElements-objects.
    """
    import Utils.ElementTreeUtils as ETUtils
    import sys
    from Utils.ProgressCounter import ProgressCounter
    from Utils.InteractionXML.CorpusElements import CorpusElements
    
    # Corpus may be in file or not
    if type(corpus) == types.StringType:
        print >> sys.stderr, "Loading corpus file", corpus
    corpusTree = ETUtils.ETFromObj(corpus)
    corpusRoot = corpusTree.getroot()
    # Use CorpusElements-class to access xml-tree
    corpusElements = CorpusElements(corpusRoot, parse, tokenization, tree=corpusTree, removeNameInfo=removeNameInfo, removeIntersentenceInteractions=removeIntersentenceInteractionsFromCorpusElements)
    print >> sys.stderr, str(len(corpusElements.documentsById)) + " documents, " + str(len(corpusElements.sentencesById)) + " sentences"
    # Make sentence graphs
    duplicateInteractionEdgesRemoved = 0
    sentences = []
    counter = ProgressCounter(len(corpusElements.sentences), "Make sentence graphs")
    counter.showMilliseconds = True
    for sentence in corpusElements.sentences[:]:
        counter.update(1, "Making sentence graphs ("+sentence.sentence.get("id")+"): ")
        # No tokens, no sentence. No also no dependencies = no sentence.
        # Let's not remove them though, so that we don't lose sentences from input.
        if len(sentence.tokens) == 0 or len(sentence.dependencies) == 0: 
            #corpusElements.sentences.remove(sentence)
            sentence.sentenceGraph = None
            continue
        for pair in sentence.pairs:
            # gif-xml defines two closely related element types, interactions and
            # pairs. Pairs are like interactions, but they can also be negative (if
            # interaction-attribute == False). Sometimes pair-elements have been
            # (incorrectly) used without this attribute. To work around these issues
            # we take all pair-elements that define interaction and add them to
            # the interaction-element list.
            isInteraction = pair.get("interaction")
            if isInteraction == "True" or isInteraction == None:
                sentence.interactions.append(pair) # add to interaction-elements
                if pair.get("type") == None: # type-attribute must be explicitly defined
                    pair.set("type", "undefined")
        # Construct the basic SentenceGraph (only syntactic information)
        graph = SentenceGraph(sentence.sentence, sentence.tokens, sentence.dependencies)
        # Add semantic information, i.e. the interactions
        graph.mapInteractions(sentence.entities, sentence.interactions)
        graph.interSentenceInteractions = sentence.interSentenceInteractions
        duplicateInteractionEdgesRemoved += graph.duplicateInteractionEdgesRemoved
        sentence.sentenceGraph = graph
        
        graph.parseElement = sentence.parseElement
        
        #graph.mapEntityHints()
    print >> sys.stderr, "Skipped", duplicateInteractionEdgesRemoved, "duplicate interaction edges in SentenceGraphs"
    return corpusElements

def getCorpusIterator(input, output, parse, tokenization=None, removeNameInfo=False, removeIntersentenceInteractions=True):
    import Utils.ElementTreeUtils as ETUtils
    from Utils.InteractionXML.SentenceElements import SentenceElements
    #import xml.etree.cElementTree as ElementTree
    
    if output != None:
        etWriter = ETUtils.ETWriter(output)
    for eTuple in ETUtils.ETIteratorFromObj(input, ("start", "end")):
        element = eTuple[1]
        if eTuple[0] in ["end", "memory"] and element.tag == "document":
            sentences = []
            for sentenceElement in element.findall("sentence"):
                #print ElementTree.tostring(sentenceElement)
                sentence = SentenceElements(sentenceElement, parse, tokenization, removeIntersentenceInteractions=removeIntersentenceInteractions)
                if len(sentence.tokens) == 0 or len(sentence.dependencies) == 0: 
                    sentence.sentenceGraph = None
                else:
                    # Construct the basic SentenceGraph (only syntactic information)
                    graph = SentenceGraph(sentence.sentence, sentence.tokens, sentence.dependencies)
                    # Add semantic information, i.e. the interactions
                    graph.mapInteractions(sentence.entities, sentence.interactions)
                    graph.interSentenceInteractions = sentence.interSentenceInteractions
                    #duplicateInteractionEdgesRemoved += graph.duplicateInteractionEdgesRemoved
                    sentence.sentenceGraph = graph
                    graph.parseElement = sentence.parseElement
                sentences.append(sentence)
            yield sentences
            if output != None:
                etWriter.write(element)
        elif element.tag == "corpus" and output != None:
            if eTuple[0] == "start":
                etWriter.begin(element)
            else:
                etWriter.end(element)
        if eTuple[0] == "end" and element.tag in ["document", "corpus"]:
            element.clear()
    if output != None:
        etWriter.close()

class SentenceGraph:
    """
    The main purpose of SentenceGraph is to connect the syntactic dependency
    parse (a graph where dependencies are edges and tokens are nodes) to the
    semantic interactions (which form a graph where interactions are edges
    and entities are nodes). Additionally, SentenceGraph provides several
    dictionaries that e.g. map element ids to their corresponding elements.
    """
    def __init__(self, sentenceElement, tokenElements, dependencyElements):
        """
        Creates the syntactic graph part of the SentenceGraph. The semantic graph
        can be added with mapInteractions.
        
        @param sentenceElement: interaction-XML sentence-element
        @type sentenceElement: cElementTree.Element
        @param tokenElements: interaction-XML syntactic token elements
        @type tokenElements: list of cElementTree.Element objects
        @param dependencyElements: interacton-XML syntactic dependency elements
        @type dependencyElements: list of cElementTree.Element objects   
        """
        self.sentenceElement = sentenceElement
        self.tokens = tokenElements
        self.dependencies = dependencyElements
        #self.dependencyGraph = NX.XDiGraph(multiedges = multiedges)
        #if multiedges:
        #    self.dependencyGraph = NX10.MultiDiGraph()
        #else:
        #    self.dependencyGraph = NX10.DiGraph()
        self.dependencyGraph = Graph()
        self.interactions = None
        self.entities = None
        self.interactionGraph = None
        self.entityGraph = None
        self.duplicateInteractionEdgesRemoved = 0
        self.tokenHeadScores = None
        # Merged graph
        self.mergedEntities = None
        self.mergedEntityToDuplicates = None
        self.mergedEntityGraph = None
        
        self.tokensById = {}
        for token in self.tokens:
            self.tokensById[token.get("id")] = token
            #self.dependencyGraph.add_node(token)
        self.dependencyGraph.addNodes(self.tokens)
        # Build the dependency graph using token-elements as nodes and dependency-elements
        # as edge data
        for dependency in self.dependencies:
            #self.dependencyGraph.add_edge(self.tokensById[dependency.attrib["t1"]],\
            self.dependencyGraph.addEdge(self.tokensById[dependency.get("t1")],\
                                          self.tokensById[dependency.get("t2")],\
                                          dependency)
            #                              element=dependency)
    
#    def getUndirectedDependencyGraph(self):
#        """
#        Create an undirected version of the syntactic dependency graph.
#        """
#        u = NX10.MultiGraph()
#        for token in self.tokens:
#            u.add_node(token)
#        for dependency in self.dependencies:
#            u.add_edge(self.tokensById[dependency.attrib["t1"]],\
#              self.tokensById[dependency.attrib["t2"]], element=dependency)
#            u.add_edge(self.tokensById[dependency.attrib["t2"]],\
#              self.tokensById[dependency.attrib["t1"]], element=dependency)
#        return u
    
    def getSentenceId(self):
        return self.sentenceElement.get("id")
    
    def makeEntityGraph(self, entities, interactions, entityToDuplicates=None):
        graph = Graph()
        graph.addNodes(entities)
        # make a dummy duplicate map if it's not required
        if entityToDuplicates == None:
            entityToDuplicates = {}
            for e in entities:
                entityToDuplicates[e] = []
        # initialize a helper map
        interactionMap = {}
        for interaction in interactions:
            e1 = self.entitiesById[interaction.get("e1")]
            e2Id = interaction.get("e2")
            if e2Id not in self.entitiesById: # intersentence interaction
                if e2Id not in entities:
                    entities.append(e2Id)
                    entityToDuplicates[e2Id] = []
                e2 = e2Id # make a dummy node
            else: 
                e2 = self.entitiesById[e2Id]
            if e1 not in interactionMap:
                interactionMap[e1] = {}
            if e2 not in interactionMap[e1]:
                interactionMap[e1][e2] = []
            interactionMap[e1][e2].append(interaction)
        # make the graph
        for e1 in entities: # loop through all given entities
            for e2 in entities: # loop through all given entities
                interactionTypes = set()
                for d1 in [e1] + entityToDuplicates[e1]: # add duplicates to each iteration
                    for d2 in [e2] + entityToDuplicates[e2]: # add duplicates to each iteration
                        if d1 in interactionMap and d2 in interactionMap[d1]:
                            for interaction in interactionMap[d1][d2]:
                                if interaction.get("type") not in interactionTypes: # remove edges with the same type that another edge already had
                                    graph.addEdge(e1, e2, interaction) # add primary and duplicate edges for the main entity pair
                                    interactionTypes.add(interaction.get("type"))
        return graph
    
    # TODO: This method shouldn't be needed anymore
    def getInteractions(self, entity1, entity2, merged=False):
        """
        Return a list of interaction-elements which represent directed
        interactions from entity1 to entity2.
        
        @param entity1: a semantic node (trigger or named entity)
        @type entity1: cElementTree.Element 
        @param entity2: a semantic node (trigger or named entity)
        @type entity2: cElementTree.Element 
        """
        if merged:
            # Note: mergeInteractionGraph must be called before
            if self.mergedEntityToDuplicates == None:
                self.mergeInteractionGraph(True)
            if self.mergedEntityGraph == None:
                self.mergedEntityGraph = self.makeEntityGraph(self.mergedEntities, self.interactions, self.mergedEntityToDuplicates)
            return self.mergedEntityGraph.getEdges(entity1, entity2)
        else:
            if self.entityGraph == None:
                self.entityGraph = self.makeEntityGraph(self.entities, self.interactions)
            return self.entityGraph.getEdges(entity1, entity2)
    
    def getOutInteractions(self, entity, merged=False):
        if merged:
            # Note: mergeInteractionGraph must be called before
            #assert self.mergedEntityToDuplicates != None
            if self.mergedEntityToDuplicates == None:
                self.mergeInteractionGraph(True)
            if self.mergedEntityGraph == None:
                self.mergedEntityGraph = self.makeEntityGraph(self.mergedEntities, self.interactions, self.mergedEntityToDuplicates)
            return self.mergedEntityGraph.getOutEdges(entity)
        else:
            if self.entityGraph == None:
                self.entityGraph = self.makeEntityGraph(self.entities, self.interactions)
            return self.entityGraph.getOutEdges(entity)

#        rv = []
#        for interaction in self.interactions:
#            if interaction.get("e1") == entity1.get("id") and interaction.get("e2") == entity2.get("id"):
#                rv.append(interaction)
#        return rv
    
    def mapInteractions(self, entityElements, interactionElements, verbose=False):
        """
        Maps the semantic interactions to the syntactic graph.
        
        Syntactic dependencies are defined between tokens. Semantic edges (interactions)
        are defined between annotated entities. To utilize the correlation of the dependency
        parse with the semantic interactions, the graphs must be aligned by mapping the
        interaction graph's nodes (entities) to the syntactic graph's nodes (tokens). This
        is done by determining the head tokens of the entities.
        
        @param entityElements: the semantic nodes (triggers and named entities)
        @type entityElements: list of cElementTree.Element objects
        @param interactionElements: the semantic edges (e.g. Cause and Theme for GENIA)
        @type interactionElements: list of cElementTree.Element objects
        @param verbose: Print selected head tokens on screen
        @param verbose: boolean
        """     
        self.interactions = interactionElements
        self.entities = entityElements
        # Entities that have no text binding can not be mapped and are therefore removed
        for entity in self.entities[:]:
            if entity.get("charOffset") == "":
                self.entities.remove(entity)
        #self.interactionGraph = NX.XDiGraph(multiedges = multiedges)
        #if multiedges:
        #    self.interactionGraph = NX10.MultiDiGraph()
        #else:
        #    self.interactionGraph = NX10.DiGraph()
        self.interactionGraph = Graph()
        self.interactionGraph.addNodes(self.tokens)
        #for token in self.tokens:
        #    self.interactionGraph.add_node(token)
        
        self.entitiesByToken = {} # a mapping for fast access
        self.entitiesById = {}
        self.entityHeadTokenByEntity = {}
        sentenceSpan = (0, len(self.sentenceElement.get("text"))) # for validating the entity offsets
        for entity in self.entities[:]:
            headToken = self.mapEntity(entity, verbose)
            if headToken != None:
                self.entityHeadTokenByEntity[entity] = headToken
                self.entitiesById[entity.get("id")] = entity
            else:
                # Check that the entity is within the sentence
                if not Range.overlap(Range.charOffsetToSingleTuple(entity.get("charOffset")), sentenceSpan):
                    raise Exception("Entity " + entity.get("id") + ", charOffset " + entity.get("charOffset") + ", does not overlap with sentence " + self.sentenceElement.get("id") + ", length " + str(sentenceSpan[1]) )
                # Assume there simply is no token corresponding to the entity
                self.entities.remove(entity)
        self._markNamedEntities()
        
        for interaction in self.interactions:
            if not self.entitiesById.has_key(interaction.get("e1")):
                continue # e1 is outside of this sentence
            if not self.entitiesById.has_key(interaction.get("e2")):
                continue # e2 is outside of this sentence
            token1 = self.entityHeadTokenByEntity[self.entitiesById[interaction.get("e1")]]
            token2 = self.entityHeadTokenByEntity[self.entitiesById[interaction.get("e2")]]
            
#            found = False
#            if multiedges:
#                edges = self.interactionGraph.get_edge_data(token1, token2, default={})
#                for i in range(len(edges)):
#                    edge = edges[i]["element"]
#                    if edge.attrib["type"] == interaction.attrib["type"]:
#                        found = True
#                        break
#            if not found:
#                self.interactionGraph.add_edge(token1, token2, element=interaction)
#            else:
#                self.duplicateInteractionEdgesRemoved += 1
            found = False
            edges = self.interactionGraph.getEdges(token1, token2)
            for edge in edges:
                if edge[2].get("type") == interaction.get("type"):
                    found = True
                    break
            if not found:
                self.interactionGraph.addEdge(token1, token2, interaction)
            else:
                # TODO: "skipped" would be better than "removed"
                self.duplicateInteractionEdgesRemoved += 1
    
    def mapEntity(self, entityElement, verbose=False):
        """
        Determine the head token for a named entity or trigger. The head token is the token closest
        to the root for the subtree of the dependency parse spanned by the text of the element.
        
        @param entityElement: a semantic node (trigger or named entity)
        @type entityElement: cElementTree.Element
        @param verbose: Print selected head tokens on screen
        @param verbose: boolean
        """
        headOffset = None
        if entityElement.get("headOffset") != None:
            headOffset = Range.charOffsetToSingleTuple(entityElement.get("headOffset"))
        if entityElement.get("charOffset") != "":
            charOffsets = Range.charOffsetToTuples(entityElement.get("charOffset"))
        else:
            charOffsets = []
        # Each entity can consist of multiple syntactic tokens, covered by its
        # charOffset-range. One of these must be chosen as the head token.
        headTokens = [] # potential head tokens
        for token in self.tokens:
            #print token.attrib["id"], token.attrib["charOffset"]
            tokenOffset = Range.charOffsetToSingleTuple(token.get("charOffset"))
            if headOffset != None and entityElement.get("type") != "Binding":
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
            selHead = None
            if entityElement.get("type") == "Binding":
                for t in headTokens:
                    compText = t.get("text").lower()
                    if compText.find("bind") != -1 or compText.find("complex") != -1:
                        selHead = t
                        #print "Head:", selHead.get("text"), "/", entityElement.get("text"), entityElement.get("headOffset"), selHead.get("charOffset")
                        entityElement.set("headOffset", selHead.get("charOffset"))
                        break
            if selHead == None: 
                token = self.findHeadToken(headTokens)
            else:
                token = selHead
            if verbose:
                print >> sys.stderr, "Selected head:", token.get("id"), token.get("text")
        #assert token != None, entityElement.get("id")
        if token != None:
            # The ElementTree entity-element is modified by setting the headOffset attribute
            if entityElement.get("headOffset") == None or entityElement.get("headOffset") != token.get("charOffset"):
                entityElement.set("headOffset", token.get("charOffset"))
            if not self.entitiesByToken.has_key(token):
                self.entitiesByToken[token] = []
            self.entitiesByToken[token].append(entityElement)
        else:
            print >> sys.stderr, "Warning, no tokens for entity", entityElement.get("id")
        return token

#    def mapEntityHints(self, verbose=False):
#        """
#        Determine the head token for a named entity or trigger. The head token is the token closest
#        to the root for the subtree of the dependency parse spanned by the text of the element.
#        
#        @param entityElement: a semantic node (trigger or named entity)
#        @type entityElement: cElementTree.Element
#        @param verbose: Print selected head tokens on screen
#        @param verbose: boolean
#        """
#        self.entityHints = self.sentenceElement.findall("entityHint")
#        self.entityHintsByToken = {}
#        for entityElement in self.entityHints:
#            headOffset = None
#            if entityElement.attrib.has_key("headOffset"):
#                headOffset = Range.charOffsetToSingleTuple(entityElement.attrib["headOffset"])
#            if entityElement.attrib["charOffset"] != "":
#                charOffsets = Range.charOffsetToTuples(entityElement.attrib["charOffset"])
#            else:
#                charOffsets = []
#            # Each entity can consist of multiple syntactic tokens, covered by its
#            # charOffset-range. One of these must be chosen as the head token.
#            headTokens = [] # potential head tokens
#            for token in self.tokens:
#                #print token.attrib["id"], token.attrib["charOffset"]
#                tokenOffset = Range.charOffsetToSingleTuple(token.attrib["charOffset"])
#                if headOffset != None:
#                    # A head token can already be defined in the headOffset-attribute.
#                    # However, depending on the tokenization, even this range may
#                    # contain multiple tokens. Still, it can always be assumed that
#                    # if headOffset is defined, the corret head token is in this range.
#                    if Range.overlap(headOffset,tokenOffset):
#                        headTokens.append(token)
#                else:
#                    for offset in charOffsets:
#                        if Range.overlap(offset,tokenOffset):
#                            headTokens.append(token)
#            if len(headTokens)==1: # An unambiguous head token was found
#                token = headTokens[0]
#            else: # One head token must be chosen from the candidates
#                token = self.findHeadToken(headTokens)
#                if verbose:
#                    print >> sys.stderr, "Selected head:", token.attrib["id"], token.attrib["text"]
#            assert token != None, entityElement.get("id")
#            if token != None:
#                # The ElementTree entity-element is modified by setting the headOffset attribute
#                if not entityElement.attrib.has_key("headOffset"):
#                    entityElement.attrib["headOffset"] = token.attrib["charOffset"]
#                if not self.entityHintsByToken.has_key(token):
#                    self.entityHintsByToken[token] = []
#                self.entityHintsByToken[token].append(entityElement)

    def findHeadToken(self, candidateTokens):
        """
        Select the candidate token that is closest to the root of the subtree of the depencdeny parse
        to which the candidate tokens belong to. See getTokenHeadScores method for the algorithm.
        
        @param candidateTokens: the list of syntactic tokens from which the head token is selected
        @type candidateTokens: list of cElementTree.Element objects
        """
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
        tokenById = {}
        for token in self.tokens:
            tokenId = token.get("id")
            assert tokenId not in tokenById
            tokenById[tokenId] = token
            self.tokenHeadScores[token] = 0 # initialize score as zero (unconnected token)
            for dependency in self.dependencies:
                if dependency.get("t1") == token.get("id") or dependency.get("t2") == token.get("id"):
                    self.tokenHeadScores[token] = 1 # token is connected by a dependency
                    break               
        
        # Give a low score for tokens that clearly can't be head and are probably produced by hyphen-splitter
        for token in self.tokens:
            tokenText = token.get("text")
            if tokenText == "\\" or tokenText == "/" or tokenText == "-":
                self.tokenHeadScores[token] = -1
        
        # Loop over all dependencies and increase the scores of all governor tokens
        # until each governor token has a higher score than its dependent token.
        # Some dependencies might form a loop so a list is used to define those
        # dependency types used in determining head scores.
        depTypesToInclude = ["prep", "nn", "det", "hyphen", "num", "amod", "nmod", "appos", "measure", "dep", "partmod"]
        #depTypesToRemoveReverse = ["A/AN"]
        modifiedScores = True
        loopCount = 0 # loopcount for devel set approx. 2-4
        while modifiedScores == True: # loop until the scores no longer change
            if loopCount > 20: # survive loops
                print >> sys.stderr, "Warning, possible loop in parse for sentence", self.getSentenceId()
                break
            modifiedScores = False
#            for token1 in self.tokens:
#                for token2 in self.tokens: # for each combination of tokens...
            for dep in self.dependencies: # ... check each dependency
                token1 = tokenById[dep.get("t1")]
                token2 = tokenById[dep.get("t2")]
                if dep.get("type") in depTypesToInclude:
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
            loopCount += 1
        
        # Add scores to tokens
        for token in self.tokens:
            token.set("headScore", str(self.tokenHeadScores[token]))
            
        return self.tokenHeadScores

    def _markNamedEntities(self):
        """
        This method is used to define which tokens belong to _named_ entities.
        Named entities are sometimes masked when testing learning of interactions, to
        prevent the system making a trivial decision based on commonly interacting names.
        This function assumes that all given entities are named entities.
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
            entityOffsets = Range.charOffsetToTuples(entity.get("charOffset"))
            entityHeadOffset = Range.charOffsetToSingleTuple(entity.get("headOffset"))
            for token in self.tokens:
                tokenOffset = Range.charOffsetToSingleTuple(token.get("charOffset"))
                for entityOffset in entityOffsets:
                    if Range.overlap(entityOffset, tokenOffset):
                        self.tokenIsEntity[token] = True
                        if entity.get("given") == "True":
                            self.tokenIsName[token] = True
#                        if entity.get("given") != None:
#                            if entity.get("given") == "True":
#                                self.tokenIsName[token] = True
#                        else:
#                            entity.set("given", "True")
#                            self.tokenIsName[token] = True
                if Range.overlap(entityHeadOffset, tokenOffset):
                    self.tokenIsEntityHead[token].append(entity)
                                                          
    def getTokenText(self, token):
        """
        Returns the text of a token, and masks it if the token is the head token
        of a named entity.
        
        @param token: interaction-XML syntactic token.
        @type token: cElementTree.Element
        """
        if self.tokenIsName[token]:
            return "NAMED_ENT"
        else:
            return token.get("text")
    
    def getCleared(self):
        c = SentenceGraph(self.sentenceElement, self.tokens, self.dependencies)
        namedEntities = []
        for entity in self.entities:
            if entity.get("given") == "True":
                namedEntities.append(entity)
        c.mapInteractions(namedEntities, [])
        return c
    
    def mergeInteractionGraph(self, merge=True):
        """
        For merging duplicate entities
        
        keepDuplicates - allows calling the function with no effect, so that the same code
                         can be used for merged and unmerged cases
        """
        self.mergedEntities = []
        self.mergedEntityToDuplicates = {}
        #duplicates = {}
        #mergedIds = {}
        if not merge: # no entities are filtered
            # Create dummy structures
            for entity in self.entities:
                mergedIds[entity] = entity.get("id")
                self.mergedEntities.append(entity)
                self.mergedEntityToDuplicates[entity] = []
            return
        # Mark all duplicates after the first one in the list for removal
        removeEntities = [False] * len(self.entities)
        entitiesToKeep = []
        for i in range(len(self.entities)): # loop through all entities, including the last one
            if removeEntities[i]: # entity has been already removed
                continue
            self.mergedEntities.append(self.entities[i])
            #mergedIds[entities[i]] = entities[i].get("id")
            self.mergedEntityToDuplicates[self.entities[i]] = []
            if self.entities[i].get("given") == "True": # named entities are never merged
                continue
            for j in range(i+1, len(self.entities)): # loop through all entities coming after entity "i"
                # Entities are duplicates if they have the same type and head token
                # Also, they are not duplicates if the charOffset differs. This shoulnd't matter,
                # as the head tokens are the same, but in practice, on the GE, task improves performance,
                # maybe due to multiple similar examples affecting SVM learning.
                if self.entities[i].get("type") == self.entities[j].get("type") and \
                   self.entities[i].get("charOffset") == self.entities[j].get("charOffset"): # and self.entityHeadTokenByEntity[self.entities[i]] == self.entityHeadTokenByEntity[self.entities[j]]:
                    removeEntities[j] = True
                    #mergedIds[entities[i]] += "/" + entities[j].get("id")
                    self.mergedEntityToDuplicates[self.entities[i]].append(self.entities[j])
        #return entitiesToKeep, mergedIds, duplicates     