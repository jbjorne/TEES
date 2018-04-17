import sys
from Detectors.KerasDetectorBase import KerasDetectorBase

class KerasTokenDetector(KerasDetectorBase):

    def __init__(self):
        KerasDetectorBase.__init__(self)
        self.useNonGiven = False
        self.exampleType = "token"
        self.defaultExtra = {}

    ###########################################################################
    # Example Generation
    ###########################################################################
        
    def buildExamplesFromGraph(self, sentenceGraph, examples, goldGraph=None):
        """
        Build one example for each token of the sentence
        """
        # determine (manually or automatically) the setting for whether sentences with no given entities should be skipped
        buildForNameless = False
        if self.structureAnalyzer and not self.structureAnalyzer.hasGroupClass("GIVEN", "ENTITY"): # no given entities points to no separate NER program being used
            buildForNameless = True
        if self.styles.get("build_for_nameless"): # manually force the setting
            buildForNameless = True
        if self.styles.get("skip_for_nameless"): # manually force the setting
            buildForNameless = False
        
        # determine whether sentences with no given entities should be skipped
        if not self.styles.get("names"):
            namedEntityCount = 0
            for entity in sentenceGraph.entities:
                assert entity.get("given") in ("True", "False", None)
                if entity.get("given") == "True": # known data which can be used for features
                    namedEntityCount += 1
            # NOTE!!! This will change the number of examples and omit
            # all triggers (positive and negative) from sentences which
            # have no NE:s, possibly giving a too-optimistic performance
            # value. Such sentences can still have triggers from intersentence
            # interactions, but as such events cannot be recovered anyway,
            # looking for these triggers would be pointless.
            if namedEntityCount == 0 and not buildForNameless: # no names, no need for triggers
                return 0 #[]
        else:
            for key in sentenceGraph.tokenIsName.keys():
                sentenceGraph.tokenIsName[key] = False

        #outfile.write("[")
        # Prepare the indices
        numTokens = len(sentenceGraph.tokens)
        #indices = [self.embeddings["words"].getIndex(sentenceGraph.tokens[i].get("text").lower(), "[out]") for i in range(numTokens)]
        self.exampleLength = int(self.styles.get("el", 21)) #31 #9 #21 #5 #3 #9 #19 #21 #9 #5 #exampleLength = self.EXAMPLE_LENGTH if self.EXAMPLE_LENGTH != None else numTokens
        
        # Pre-generate features for all tokens in the sentence
        tokens, tokenMap = self.getTokenFeatures(sentenceGraph)
        
        dg = sentenceGraph.dependencyGraph
        undirected = dg.toUndirected()
        edgeCounts = {x:len(dg.getInEdges(x) + dg.getOutEdges(x)) for x in sentenceGraph.tokens}
        
        exampleNodes = []
        if self.exampleType == "entity":
            exampleNodes = [{"entity":x, "token":sentenceGraph.entityHeadTokenByEntity[x]} for x in sentenceGraph.entities if not entity.get("given")]
        else:
            assert self.exampleType == "token"
            exampleNodes = [{"entity":None, "token":x} for x in sentenceGraph.tokens]
        
        for i in range(len(exampleNodes)):
            token = exampleNodes[i]["token"]
            entity = exampleNodes[i]["entity"]
            
            if self.exampleType == "entity":
                labels, entityIds = self.getEntityTypes([entity])
            else:
                labels, entityIds = self.getEntityTypes(sentenceGraph.tokenIsEntityHead[token])

            # CLASS
            #labels = self.getEntityTypes(sentenceGraph.tokenIsEntityHead[token])
            self.exampleStats.beginExample(",".join(labels))
            
            # Recognize only non-named entities (i.e. interaction words)
            if sentenceGraph.tokenIsName[token] and not self.styles.get("names") and not self.styles.get("all_tokens"):
                self.exampleStats.filter("name")
                self.exampleStats.endExample()
                continue
            
            featureGroups = sorted(self.embeddings.keys())
            wordEmbeddings = [x for x in featureGroups if self.embeddings[x].wvPath != None]
            #tokens = []
            features = {x:[] for x in self.embeddingInputs.keys()} #{"words":[], "positions":[], "named_entities":[], "POS":[], "gold":[]}
            featureGroups = sorted(features.keys())
            side = (self.exampleLength - 1) / 2
            windowIndex = 0
            for j in range(i - side, i + side + 1):
                if j >= 0 and j < numTokens:
                    token2 = tokens[j]
                    #tokens.append(token2)
                    #if self.debugGold:
                    #    self.addFeature("gold", features, ",".join(labels[j]), "[out]")
                    for wordEmbedding in wordEmbeddings:
                        self.addIndex(wordEmbedding, features, token2[wordEmbedding])
                    #self.addFeature("positions", features, self.getPositionName(j - i), "[out]")
                    self.addFeature("positions", features, str(windowIndex), "[out]")
                    if self.useNonGiven:
                        self.addIndex("entities", features, token2["entities"])
                    else:
                        self.addIndex("named_entities", features, token2["named_entities"])
                    self.addIndex("POS", features, token2["POS"])
                    self.addPathEmbedding(token, token2["element"], sentenceGraph.dependencyGraph, undirected, edgeCounts, features)
                else:
                    #tokens.append(None)
                    for featureGroup in featureGroups:
                        self.addFeature(featureGroup, features, "[pad]")
                windowIndex += 1
            
            extra = {"t":token.get("id"), "entity":entity.get("id") if entity != None else None}
            extra.update(self.defaultExtra)
            if entityIds != None:
                extra["goldIds"] = "/".join(entityIds) # The entities to which this example corresponds
            if self.styles.get("epi_merge_negated"):
                extra["unmergeneg"] = "epi" # Request trigger type unmerging
            examples.append({"id":sentenceGraph.getSentenceId()+".x"+str(self.exampleIndex), "labels":labels, "features":features, "extra":extra, "doc":sentenceGraph.documentElement.get("id")}) #, "extra":{"eIds":entityIds}}
            self.exampleIndex += 1
            self.exampleStats.endExample()
    
    def getEntityTypes(self, entities, useNeg=False):
        raise NotImplementedError
    
    def defineFeatureGroups(self):
        print >> sys.stderr, "Defining embedding indices"
        self.defineWordEmbeddings()
        self.defineEmbedding("positions")
        if self.useNonGiven:
            self.defineEmbedding("entities")
        else:
            self.defineEmbedding("named_entities")
        self.defineEmbedding("POS", vocabularyType="POS")
        for name in ["path" + str(i) for i in range(self.pathDepth)]:
            self.defineEmbedding(name, vocabularyType="directed_dependencies")
        #self.defineEmbedding("path", vocabularyType="directed_dependencies", inputNames=["path" + str(i) for i in range(self.pathDepth)])
        #if self.debugGold:
        #    self.defineEmbedding("gold")