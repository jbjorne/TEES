import sys
sys.path.append("..")
import Utils.Libraries.PorterStemmer as PorterStemmer
from Core.IdSet import IdSet
import Core.ExampleUtils as ExampleUtils
#from Core.Gazetteer import Gazetteer
from FeatureBuilder import FeatureBuilder

#def compareDependencyEdgesById(dep1, dep2):
#    """
#    Dependency edges are sorted, so that the program behaves consistently
#    on the sama data between different runs.
#    """
#    id1 = dep1[2].get("id")
#    id2 = dep2[2].get("id")
#    if id1 > id2:
#       return 1
#    elif id1 == id2:
#       return 0
#    else: # x<y
#       return -1

class TriggerFeatureBuilder(FeatureBuilder):
    def __init__(self, featureSet, style=None):
        FeatureBuilder.__init__(self, featureSet, style)
        self.noAnnType = False
        self.edgeTypesForFeatures = []
        self.useNonNameEntities = False

    def getMergedEntityType(self, entities):
        """
        If a single token belongs to multiple entities of different types,
        a new, composite type is defined. This type is the alphabetically
        ordered types of these entities joined with '---'.
        """
        types = set()
        for entity in entities:
            types.add(entity.get("type"))
        types = list(types)
        types.sort()
        typeString = ""
        for type in types:
            if typeString != "":
                typeString += "---"
            typeString += type
        return typeString
    
    def getTokenFeatures(self, token, sentenceGraph):
        """
        Returns a list of features based on the attributes of a token.
        These can be used to define more complex features.
        """
        # These features are cached when this method is first called
        # for a token.
        if self.tokenFeatures.has_key(token):
            return self.tokenFeatures[token], self.tokenFeatureWeights[token]
        tokTxt=sentenceGraph.getTokenText(token)
        features = {}
        features["_txt_"+tokTxt]=1
        features["_POS_"+token.get("POS")]=1
        if sentenceGraph.tokenIsName[token]:
            features["_given"]=1
            for entity in sentenceGraph.tokenIsEntityHead[token]:
                if entity.get("given") == "True":
                    features["_annType_"+self.getEntityType(entity)]=1
        # Only for Unmerging!
        if self.useNonNameEntities:
            for entity in sentenceGraph.tokenIsEntityHead[token]:
                features["_annType_"+self.getEntityType(entity)]=1
#        if self.gazetteer and tokTxt.lower() in self.gazetteer:
#            for label,weight in self.gazetteer[tokTxt.lower()].items():
#                pass
#                #features["_knownLabel_"+label]=weight
        self.tokenFeatures[token] = sorted(features.keys())
        self.tokenFeatureWeights[token] = features
        return self.tokenFeatures[token], self.tokenFeatureWeights[token]
    
    def buildLinearOrderFeatures(self,sentenceGraph,index,tag):
        """
        Linear features are built by marking token features with a tag
        that defines their relative position in the linear order.
        """
        tag = "linear_"+tag
        tokenFeatures, tokenFeatureWeights = self.getTokenFeatures(sentenceGraph.tokens[index], sentenceGraph)
        for tokenFeature in tokenFeatures:
            self.setFeature(tag+tokenFeature, tokenFeatureWeights[tokenFeature])
    
    def initSentence(self, sentenceGraph):
        """
        Build one example for each token of the sentence
        """
        self.sentenceGraph = sentenceGraph
        self.tokenFeatures = {}
        self.tokenFeatureWeights = {}
        
        #if not "names" in self.styles:
        namedEntityCount = 0
        for entity in sentenceGraph.entities:
            if entity.get("given") == "True": # known data which can be used for features
                namedEntityCount += 1
        self.namedEntityCountFeature = "nameCount_" + str(namedEntityCount)
        
        bagOfWords = {}
        for token in sentenceGraph.tokens:
            text = "bow_" + token.get("text")
            if not bagOfWords.has_key(text):
                bagOfWords[text] = 0
            bagOfWords[text] += 1
            if sentenceGraph.tokenIsName[token]:
                text = "ne_" + text
                if not bagOfWords.has_key(text):
                    bagOfWords[text] = 0
                bagOfWords[text] += 1
        self.bowFeatures = {}
        for k in sorted(bagOfWords.keys()):
            self.bowFeatures[self.featureSet.getId(k)] = bagOfWords[k]
        
        self.inEdgesByToken = {}
        self.outEdgesByToken = {}
        self.edgeSetByToken = {}
        for token in sentenceGraph.tokens:
            inEdges = sentenceGraph.dependencyGraph.getInEdges(token)
            #inEdges = sentenceGraph.dependencyGraph.in_edges(token, data=True)
            #fixedInEdges = []
            #for edge in inEdges:
            #    fixedInEdges.append( (edge[0], edge[1], edge[2]["element"]) )
            #inEdges = fixedInEdges
            #inEdges.sort(compareDependencyEdgesById)
            self.inEdgesByToken[token] = inEdges
            
            outEdges = sentenceGraph.dependencyGraph.getOutEdges(token)
            #outEdges = sentenceGraph.dependencyGraph.out_edges(token, data=True)
            #fixedOutEdges = []
            #for edge in outEdges:
            #    fixedOutEdges.append( (edge[0], edge[1], edge[2]["element"]) )
            #outEdges = fixedOutEdges
            #outEdges.sort(compareDependencyEdgesById)
            self.outEdgesByToken[token] = outEdges
            self.edgeSetByToken[token] = set(inEdges + outEdges)
        
    def buildFeatures(self, token, linear=True, chains=True):
        sentenceGraph = self.sentenceGraph
        tokenIndex = None
        for i in range(len(self.sentenceGraph.tokens)):
            if token == self.sentenceGraph.tokens[i]:
                tokenIndex = i
                break
        assert tokenIndex != None
        token = self.sentenceGraph.tokens[tokenIndex]
        
        #if not "names" in self.styles:
        self.setFeature(self.namedEntityCountFeature, 1)
        
        #self.features.update(self.bowFeatures) # Note! these do not get tagged
        
#            for j in range(len(sentenceGraph.tokens)):
#                text = "bow_" + sentenceGraph.tokens[j].get("text")
#                if j < i:
#                    features[self.featureSet.getId("bf_" + text)] = 1
#                elif j > i:
#                    features[self.featureSet.getId("af_" + text)] = 1
    
        # Main features
        text = token.get("text")
        self.setFeature("txt_"+text, 1)
        self.setFeature("POS_"+token.get("POS"), 1)
        stem = PorterStemmer.stem(text)
        self.setFeature("stem_"+stem, 1)
        self.setFeature("nonstem_"+text[len(stem):], 1)
        
        # Linear order features
        if linear:
            for index in [-3,-2,-1,1,2,3]:
                if i + index > 0 and i + index < len(sentenceGraph.tokens):
                    self.buildLinearOrderFeatures(sentenceGraph, i + index, str(index))
        
        # Content
        if i > 0 and text[0].isalpha() and text[0].isupper():
            self.setFeature("upper_case_start", 1)
        for j in range(len(text)):
            if j > 0 and text[j].isalpha() and text[j].isupper():
                self.setFeature("upper_case_middle", 1)
            # numbers and special characters
            if text[j].isdigit():
                self.setFeature("has_digits", 1)
                if j > 0 and text[j-1] == "-":
                    self.setFeature("has_hyphenated_digit", 1)
            elif text[j] == "-":
                self.setFeature("has_hyphen", 1)
            elif text[j] == "/":
                self.setFeature("has_fslash", 1)
            elif text[j] == "\\":
                self.setFeature("has_bslash", 1)
            # duplets
            if j > 0:
                self.setFeature("dt_"+text[j-1:j+1].lower(), 1)
            # triplets
            if j > 1:
                self.setFeature("tt_"+text[j-2:j+1].lower(), 1)
        
        # chains
        if chains:
            self.buildChains(token, sentenceGraph)

    def buildAttachedEdgeFeatures(self, token, sentenceGraph):
        # Attached edges (Hanging in and out edges)
        t1InEdges = self.inEdgesByToken[token]
        for edge in t1InEdges:
            edgeType = edge[2].get("type")
            self.setFeature("t1HIn_"+edgeType, 1)
            self.setFeature("t1HIn_"+edge[0].get("POS"), 1)
            self.setFeature("t1HIn_"+edgeType+"_"+edge[0].get("POS"), 1)
            tokenText = sentenceGraph.getTokenText(edge[0])
            self.setFeature("t1HIn_"+tokenText, 1)
            self.setFeature("t1HIn_"+edgeType+"_"+tokenText, 1)
        t1OutEdges = self.outEdgesByToken[token]
        for edge in t1OutEdges:
            edgeType = edge[2].get("type")
            self.setFeature("t1HOut_"+edgeType, 1)
            self.setFeature("t1HOut_"+edge[1].get("POS"), 1)
            self.setFeature("t1HOut_"+edgeType+"_"+edge[1].get("POS"), 1)
            tokenText = sentenceGraph.getTokenText(edge[1])
            self.setFeature("t1HOut_"+tokenText, 1)
            self.setFeature("t1HOut_"+edgeType+"_"+tokenText, 1)
    
    def buildChains(self,token,sentenceGraph,depthLeft=3,chain="",visited=None):
        if depthLeft == 0:
            return
        strDepthLeft = "dist_" + str(depthLeft)
        
        if visited == None:
            visited = set()

        inEdges = self.inEdgesByToken[token]
        outEdges = self.outEdgesByToken[token]
        edgeSet = visited.union(self.edgeSetByToken[token])
        for edge in inEdges:
            if not edge in visited:
                edgeType = edge[2].get("type")
                self.setFeature("dep_"+strDepthLeft+edgeType, 1)

                nextToken = edge[0]
                tokenFeatures, tokenWeights = self.getTokenFeatures(nextToken, sentenceGraph)
                for tokenFeature in tokenFeatures:
                    self.setFeature(strDepthLeft + tokenFeature, tokenWeights[tokenFeature])
#                for entity in sentenceGraph.tokenIsEntityHead[nextToken]:
#                    if entity.get("given") == "True":
#                        features[self.featureSet.getId("name_dist_"+strDepthLeft)] = 1
#                        features[self.featureSet.getId("name_dist_"+strDepthLeft+entity.get("type"))] = 1
#                features[self.featureSet.getId("POS_dist_"+strDepthLeft+nextToken.get("POS"))] = 1
#                tokenText = sentenceGraph.getTokenText(nextToken)
#                features[self.featureSet.getId("text_dist_"+strDepthLeft+tokenText)] = 1
                
                self.setFeature("chain_dist_"+strDepthLeft+chain+"-frw_"+edgeType, 1)
                self.buildChains(nextToken,sentenceGraph,depthLeft-1,chain+"-frw_"+edgeType,edgeSet)

        for edge in outEdges:
            if not edge in visited:
                edgeType = edge[2].get("type")
                self.setFeature("dep_dist_"+strDepthLeft+edgeType, 1)

                nextToken = edge[1]
                tokenFeatures, tokenWeights = self.getTokenFeatures(nextToken, sentenceGraph)
                for tokenFeature in tokenFeatures:
                    self.setFeature(strDepthLeft + tokenFeature, tokenWeights[tokenFeature])
#                for entity in sentenceGraph.tokenIsEntityHead[nextToken]:
#                    if entity.get("given") == "True":
#                        features[self.featureSet.getId("name_dist_"+strDepthLeft)] = 1
#                        features[self.featureSet.getId("name_dist_"+strDepthLeft+entity.get("type"))] = 1
#                features[self.featureSet.getId("POS_dist_"+strDepthLeft+nextToken.get("POS"))] = 1
#                tokenText = sentenceGraph.getTokenText(nextToken)
#                features[self.featureSet.getId("text_dist_"+strDepthLeft+tokenText)] = 1
                
                self.setFeature("chain_dist_"+strDepthLeft+chain+"-rev_"+edgeType, 1)
                self.buildChains(nextToken,sentenceGraph,depthLeft-1,chain+"-rev_"+edgeType,edgeSet)
