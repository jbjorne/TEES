"""
Trigger examples
"""
__version__ = "$Revision: 1.29 $"

import sys, os
thisPath = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(thisPath,"..")))
import Core.ExampleBuilder
from Core.ExampleBuilder import ExampleBuilder
import Stemming.PorterStemmer as PorterStemmer
from Core.IdSet import IdSet
import Core.ExampleUtils as ExampleUtils
from Core.Gazetteer import Gazetteer
from FeatureBuilders.RELFeatureBuilder import RELFeatureBuilder

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

class GeneralEntityTypeRecognizerGztr(ExampleBuilder):
    def __init__(self, style=None, classSet=None, featureSet=None, gazetteerFileName=None, skiplist=None):
        if classSet == None:
            classSet = IdSet(1)
        assert( classSet.getId("neg") == 1 )
        if featureSet == None:
            featureSet = IdSet()
        
        ExampleBuilder.__init__(self, classSet, featureSet)
        #gazetteerFileName="/usr/share/biotext/GeniaChallenge/SharedTaskTriggerTest/gazetteer-train"
        if gazetteerFileName!=None:
            self.gazetteer=Gazetteer.loadGztr(gazetteerFileName)
            print >> sys.stderr, "Loaded gazetteer from",gazetteerFileName
        else:
            print >> sys.stderr, "No gazetteer loaded"
            self.gazetteer=None
        self.styles = style
        
        self.skiplist = set()
        if skiplist != None:
            f = open(skiplist, "rt")
            for line in f.readlines():
                self.skiplist.add(line.strip())
            f.close()
        
        if "rel_features" in self.styles:
            self.relFeatureBuilder = RELFeatureBuilder(featureSet)

    @classmethod
    def run(cls, input, output, parse, tokenization, style, idFileTag=None, gazetteerFileName=None, skiplist=None):
        if skiplist == "PubMed100p":
            skiplist = os.path.dirname(os.path.abspath(__file__))+"/Filters/PubMed100pSkipList.txt"
        
        classSet, featureSet = cls.getIdSets(idFileTag)
        e = GeneralEntityTypeRecognizerGztr(style, classSet, featureSet, gazetteerFileName, skiplist=skiplist)
        if "names" in style:
            sentences = cls.getSentences(input, parse, tokenization, removeNameInfo=True)
        else:
            sentences = cls.getSentences(input, parse, tokenization, removeNameInfo=False)
        e.buildExamplesForSentences(sentences, output, idFileTag)


    def preProcessExamples(self, allExamples):
        if "normalize" in self.styles:
            print >> sys.stderr, " Normalizing feature vectors"
            ExampleUtils.normalizeFeatureVectors(allExamples)
        return allExamples   
    
    def getMergedEntityType(self, entities):
        """
        If a single token belongs to multiple entities of different types,
        a new, composite type is defined. This type is the alphabetically
        ordered types of these entities joined with '---'.
        """
        types = set()
        for entity in entities:
            if entity.get("isName") == "True" and "all_tokens" in self.styles:
                continue
            types.add(entity.get("type"))
        types = list(types)
        types.sort()
        typeString = ""
        for type in types:
            #if type == "Protein" and "all_tokens" in self.styles:
            #    continue
            if typeString != "":
                typeString += "---"
            typeString += type
        
        if typeString == "":
            return "neg"
        
        if "limit_merged_types" in self.styles:
            if typeString.find("---") != -1:
                if typeString == "Gene_expression---Positive_regulation":
                    return typeString
                else:
                    return typeString.split("---")[0]
            else:
                return typeString
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
            features["_isName"]=1
            for entity in sentenceGraph.tokenIsEntityHead[token]:
                if entity.get("isName") == "True":
                    features["_annType_"+entity.get("type")]=1
        # Filip's gazetteer based features (can be used separately from exclude_gazetteer)
        if "gazetteer_features" in self.styles:
            tokTxtLower = tokTxt.lower()
            if "stem_gazetteer" in self.styles:
                tokTxtLower = PorterStemmer.stem(tokTxtLower)
            if self.gazetteer and tokTxtLower in self.gazetteer:
                for label,weight in self.gazetteer[tokTxtLower].items():
                    features["_knownLabel_"+label]=weight # 1 performs slightly worse
        ## BANNER features
        #if sentenceGraph.entityHintsByToken.has_key(token):
        #    features["BANNER-entity"] = 1
        self.tokenFeatures[token] = sorted(features.keys())
        self.tokenFeatureWeights[token] = features
        return self.tokenFeatures[token], self.tokenFeatureWeights[token]
    
    def buildLinearOrderFeatures(self,sentenceGraph,index,tag,features):
        """
        Linear features are built by marking token features with a tag
        that defines their relative position in the linear order.
        """
        tag = "linear_"+tag
        tokenFeatures, tokenFeatureWeights = self.getTokenFeatures(sentenceGraph.tokens[index], sentenceGraph)
        for tokenFeature in tokenFeatures:
            features[self.featureSet.getId(tag+tokenFeature)] = tokenFeatureWeights[tokenFeature]
    
    def buildLinearNGram(self, i, j, sentenceGraph, features):
        ngram = "ngram"
        for index in range(i, j+1):
            ngram += "_" + sentenceGraph.getTokenText(sentenceGraph.tokens[index]).lower()
        features[self.featureSet.getId(ngram)] = 1
    
    def buildExamples(self, sentenceGraph):
        """
        Build one example for each token of the sentence
        """
        if sentenceGraph.sentenceElement.get("origId") in self.skiplist:
            print >> sys.stderr, "Skipping sentence", sentenceGraph.sentenceElement.get("origId") 
            return []
        
        examples = []
        exampleIndex = 0
        
        self.tokenFeatures = {}
        self.tokenFeatureWeights = {}
        
        namedEntityHeadTokens = []
        if not "names" in self.styles:
            namedEntityCount = 0
            for entity in sentenceGraph.entities:
                if entity.get("isName") == "True": # known data which can be used for features
                    namedEntityCount += 1
            namedEntityCountFeature = "nameCount_" + str(namedEntityCount)
            # NOTE!!! This will change the number of examples and omit
            # all triggers (positive and negative) from sentences which
            # have no NE:s, possibly giving a too-optimistic performance
            # value. Such sentences can still have triggers from intersentence
            # interactions, but as such events cannot be recovered anyway,
            # looking for these triggers would be pointless.
            if namedEntityCount == 0: # no names, no need for triggers
                return []
            
            if "pos_pairs" in self.styles:
                namedEntityHeadTokens = self.getNamedEntityHeadTokens(sentenceGraph)
        
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
        bowFeatures = {}
        for k in sorted(bagOfWords.keys()):
            bowFeatures[self.featureSet.getId(k)] = bagOfWords[k]
        
        self.inEdgesByToken = {}
        self.outEdgesByToken = {}
        self.edgeSetByToken = {}
        for token in sentenceGraph.tokens:
            #inEdges = sentenceGraph.dependencyGraph.in_edges(token, data=True)
            #fixedInEdges = []
            #for edge in inEdges:
            #    fixedInEdges.append( (edge[0], edge[1], edge[2]["element"]) )
            #inEdges = fixedInEdges
            inEdges = sentenceGraph.dependencyGraph.getInEdges(token)
            #inEdges.sort(compareDependencyEdgesById)
            self.inEdgesByToken[token] = inEdges
            #outEdges = sentenceGraph.dependencyGraph.out_edges(token, data=True)
            #fixedOutEdges = []
            #for edge in outEdges:
            #    fixedOutEdges.append( (edge[0], edge[1], edge[2]["element"]) )
            #outEdges = fixedOutEdges
            outEdges = sentenceGraph.dependencyGraph.getOutEdges(token)
            #outEdges.sort(compareDependencyEdgesById)
            self.outEdgesByToken[token] = outEdges
            self.edgeSetByToken[token] = set(inEdges + outEdges)
        
        for i in range(len(sentenceGraph.tokens)):
            token = sentenceGraph.tokens[i]

            # CLASS
            if len(sentenceGraph.tokenIsEntityHead[token]) > 0:
                categoryName = self.getMergedEntityType(sentenceGraph.tokenIsEntityHead[token])
            else:
                categoryName = "neg"
            self.exampleStats.beginExample(categoryName)
            
            # Recognize only non-named entities (i.e. interaction words)
            if sentenceGraph.tokenIsName[token] and not "names" in self.styles and not "all_tokens" in self.styles:
                self.exampleStats.filter("name")
                self.exampleStats.endExample()
                continue

            category = self.classSet.getId(categoryName)            
            
            tokenText = token.get("text").lower()
            if "stem_gazetteer" in self.styles:
                tokenText = PorterStemmer.stem(tokenText)
            if ("exclude_gazetteer" in self.styles) and self.gazetteer and tokenText not in self.gazetteer:
                features = {}
                features[self.featureSet.getId("exclude_gazetteer")] = 1
                extra = {"xtype":"token","t":token.get("id"),"excluded":"True"}
                examples.append( (sentenceGraph.getSentenceId()+".x"+str(exampleIndex),category,features,extra) )
                exampleIndex += 1
                continue
            
            # FEATURES
            features = {}
            
            if not "names" in self.styles:
                features[self.featureSet.getId(namedEntityCountFeature)] = 1
            #for k,v in bagOfWords.iteritems():
            #    features[self.featureSet.getId(k)] = v
            # pre-calculate bow _features_
            features.update(bowFeatures)
            
#            for j in range(len(sentenceGraph.tokens)):
#                text = "bow_" + sentenceGraph.tokens[j].get("text")
#                if j < i:
#                    features[self.featureSet.getId("bf_" + text)] = 1
#                elif j > i:
#                    features[self.featureSet.getId("af_" + text)] = 1
        
            # Main features
            text = token.get("text")
            features[self.featureSet.getId("txt_"+text)] = 1
            features[self.featureSet.getId("POS_"+token.get("POS"))] = 1
            stem = PorterStemmer.stem(text)
            features[self.featureSet.getId("stem_"+stem)] = 1
            features[self.featureSet.getId("nonstem_"+text[len(stem):])] = 1

            # Normalized versions of the string (if same as non-normalized, overlap without effect)
            normalizedText = text.replace("-","").replace("/","").replace(",","").replace("\\","").replace(" ","").lower()
            if normalizedText == "bound": # should be for all irregular verbs
                normalizedText = "bind"
            features[self.featureSet.getId("txt_"+normalizedText)] = 1
            norStem = PorterStemmer.stem(normalizedText)
            features[self.featureSet.getId("stem_"+norStem)] = 1
            features[self.featureSet.getId("nonstem_"+normalizedText[len(norStem):])] = 1
            
            # Substring features
            for string in text.split("-"):
                stringLower = string.lower()
                features[self.featureSet.getId("substring_"+stringLower)] = 1
                features[self.featureSet.getId("substringstem_"+PorterStemmer.stem(stringLower))] = 1
            
            # Linear order features
            for index in [-3,-2,-1,1,2,3]:
                if i + index > 0 and i + index < len(sentenceGraph.tokens):
                    self.buildLinearOrderFeatures(sentenceGraph, i + index, str(index), features)

            # Linear n-grams
            if "linear_ngrams" in self.styles:
                self.buildLinearNGram(max(0, i-1), i, sentenceGraph, features)
                self.buildLinearNGram(max(0, i-2), i, sentenceGraph, features)
            
            if "phospho" in self.styles:
                if text.find("hospho") != -1:
                    features[self.featureSet.getId("phospho_found")] = 1
                features[self.featureSet.getId("begin_"+text[0:2].lower())] = 1
                features[self.featureSet.getId("begin_"+text[0:3].lower())] = 1
            
            # Content
            if i > 0 and text[0].isalpha() and text[0].isupper():
                features[self.featureSet.getId("upper_case_start")] = 1
            for j in range(len(text)):
                if j > 0 and text[j].isalpha() and text[j].isupper():
                    features[self.featureSet.getId("upper_case_middle")] = 1
                # numbers and special characters
                if text[j].isdigit():
                    features[self.featureSet.getId("has_digits")] = 1
                    if j > 0 and text[j-1] == "-":
                        features[self.featureSet.getId("has_hyphenated_digit")] = 1
                elif text[j] == "-":
                    features[self.featureSet.getId("has_hyphen")] = 1
                elif text[j] == "/":
                    features[self.featureSet.getId("has_fslash")] = 1
                elif text[j] == "\\":
                    features[self.featureSet.getId("has_bslash")] = 1
                # duplets
                if j > 0:
                    features[self.featureSet.getId("dt_"+text[j-1:j+1].lower())] = 1
                # triplets
                if j > 1:
                    features[self.featureSet.getId("tt_"+text[j-2:j+1].lower())] = 1
                # quadruplets (don't work, slight decrease (0.5 pp) on f-score
                #if j > 2:
                #    features[self.featureSet.getId("qt_"+text[j-3:j+1].lower())] = 1
            
            # Attached edges (Hanging in and out edges)
            t1InEdges = self.inEdgesByToken[token]
            for edge in t1InEdges:
                edgeType = edge[2].get("type")
                features[self.featureSet.getId("t1HIn_"+edgeType)] = 1
                features[self.featureSet.getId("t1HIn_"+edge[0].get("POS"))] = 1
                features[self.featureSet.getId("t1HIn_"+edgeType+"_"+edge[0].get("POS"))] = 1
                tokenText = sentenceGraph.getTokenText(edge[0])
                features[self.featureSet.getId("t1HIn_"+tokenText)] = 1
                features[self.featureSet.getId("t1HIn_"+edgeType+"_"+tokenText)] = 1
                tokenStem = PorterStemmer.stem(tokenText)
                features[self.featureSet.getId("t1HIn_"+tokenStem)] = 1
                features[self.featureSet.getId("t1HIn_"+edgeType+"_"+tokenStem)] = 1
                features[self.featureSet.getId("t1HIn_"+norStem+"_"+edgeType+"_"+tokenStem)] = 1
            t1OutEdges = self.outEdgesByToken[token]
            for edge in t1OutEdges:
                edgeType = edge[2].get("type")
                features[self.featureSet.getId("t1HOut_"+edgeType)] = 1
                features[self.featureSet.getId("t1HOut_"+edge[1].get("POS"))] = 1
                features[self.featureSet.getId("t1HOut_"+edgeType+"_"+edge[1].get("POS"))] = 1
                tokenText = sentenceGraph.getTokenText(edge[1])
                features[self.featureSet.getId("t1HOut_"+tokenText)] = 1
                features[self.featureSet.getId("t1HOut_"+edgeType+"_"+tokenText)] = 1
                tokenStem = PorterStemmer.stem(tokenText)
                features[self.featureSet.getId("t1HOut_"+tokenStem)] = 1
                features[self.featureSet.getId("t1HOut_"+edgeType+"_"+tokenStem)] = 1
                features[self.featureSet.getId("t1HOut_"+norStem+"_"+edgeType+"_"+tokenStem)] = 1
            
            # REL features
            if "rel_features" in self.styles:
                self.relFeatureBuilder.setFeatureVector(features)
                self.relFeatureBuilder.buildAllFeatures(sentenceGraph.tokens, i)
                self.relFeatureBuilder.setFeatureVector(None)
             
            extra = {"xtype":"token","t":token.get("id")}
            examples.append( (sentenceGraph.getSentenceId()+".x"+str(exampleIndex),category,features,extra) )
            exampleIndex += 1
            self.exampleStats.endExample()
            
            # chains
            self.buildChains(token, sentenceGraph, features)
            
            if "pos_pairs" in self.styles:
                self.buildPOSPairs(token, namedEntityHeadTokens, features)
        return examples
    
    def buildChains(self,token,sentenceGraph,features,depthLeft=3,chain="",visited=None):
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
                features[self.featureSet.getId("dep_"+strDepthLeft+edgeType)] = 1

                nextToken = edge[0]
                tokenFeatures, tokenWeights = self.getTokenFeatures(nextToken, sentenceGraph)
                for tokenFeature in tokenFeatures:
                    features[self.featureSet.getId(strDepthLeft + tokenFeature)] = tokenWeights[tokenFeature]
#                for entity in sentenceGraph.tokenIsEntityHead[nextToken]:
#                    if entity.get("isName") == "True":
#                        features[self.featureSet.getId("name_dist_"+strDepthLeft)] = 1
#                        features[self.featureSet.getId("name_dist_"+strDepthLeft+entity.get("type"))] = 1
#                features[self.featureSet.getId("POS_dist_"+strDepthLeft+nextToken.get("POS"))] = 1
#                tokenText = sentenceGraph.getTokenText(nextToken)
#                features[self.featureSet.getId("text_dist_"+strDepthLeft+tokenText)] = 1
                
                if sentenceGraph.tokenIsName[nextToken]:
                    features[self.featureSet.getId("name_chain_dist_"+strDepthLeft+chain+"-frw_"+edgeType)] = 1
                features[self.featureSet.getId("chain_dist_"+strDepthLeft+chain+"-frw_"+edgeType)] = 1
                self.buildChains(nextToken,sentenceGraph,features,depthLeft-1,chain+"-frw_"+edgeType,edgeSet)

        for edge in outEdges:
            if not edge in visited:
                edgeType = edge[2].get("type")
                features[self.featureSet.getId("dep_dist_"+strDepthLeft+edgeType)] = 1

                nextToken = edge[1]
                tokenFeatures, tokenWeights = self.getTokenFeatures(nextToken, sentenceGraph)
                for tokenFeature in tokenFeatures:
                    features[self.featureSet.getId(strDepthLeft + tokenFeature)] = tokenWeights[tokenFeature]
#                for entity in sentenceGraph.tokenIsEntityHead[nextToken]:
#                    if entity.get("isName") == "True":
#                        features[self.featureSet.getId("name_dist_"+strDepthLeft)] = 1
#                        features[self.featureSet.getId("name_dist_"+strDepthLeft+entity.get("type"))] = 1
#                features[self.featureSet.getId("POS_dist_"+strDepthLeft+nextToken.get("POS"))] = 1
#                tokenText = sentenceGraph.getTokenText(nextToken)
#                features[self.featureSet.getId("text_dist_"+strDepthLeft+tokenText)] = 1
                if sentenceGraph.tokenIsName[nextToken]:
                    features[self.featureSet.getId("name_chain_dist_"+strDepthLeft+chain+"-rev_"+edgeType)] = 1
                
                features[self.featureSet.getId("chain_dist_"+strDepthLeft+chain+"-rev_"+edgeType)] = 1
                self.buildChains(nextToken,sentenceGraph,features,depthLeft-1,chain+"-rev_"+edgeType,edgeSet)
    
    def getNamedEntityHeadTokens(self, sentenceGraph):
        headTokens = []
        for entity in sentenceGraph.entities:
            if entity.get("isName") == "True": # known data which can be used for features
                headTokens.append(sentenceGraph.entityHeadTokenByEntity[entity])
        return headTokens
                
    def buildPOSPairs(self, token, namedEntityHeadTokens, features):
        tokenPOS = token.get("POS")
        assert tokenPOS != None
        for headToken in namedEntityHeadTokens:
            headPOS = headToken.get("POS")
            features[self.featureSet.getId("POS_pair_NE_"+tokenPOS+"-"+headPOS)] = 1