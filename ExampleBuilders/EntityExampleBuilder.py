"""
Trigger examples
"""
__version__ = "$Revision: 1.34 $"

import sys, os
thisPath = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(thisPath,"..")))
from ExampleBuilder import ExampleBuilder
import Utils.Libraries.PorterStemmer as PorterStemmer
from Core.IdSet import IdSet
import Core.ExampleUtils as ExampleUtils
#from Core.Gazetteer import Gazetteer
from FeatureBuilders.RELFeatureBuilder import RELFeatureBuilder
from FeatureBuilders.WordNetFeatureBuilder import WordNetFeatureBuilder
from FeatureBuilders.GiulianoFeatureBuilder import GiulianoFeatureBuilder
from FeatureBuilders.DrugFeatureBuilder import DrugFeatureBuilder
import PhraseTriggerExampleBuilder
import Utils.InteractionXML.ResolveEPITriggerTypes
import Utils.Range as Range

class EntityExampleBuilder(ExampleBuilder):
    def __init__(self, style=None, classSet=None, featureSet=None, gazetteerFileName=None, skiplist=None):
        if classSet == None:
            classSet = IdSet(1)
        if featureSet == None:
            featureSet = IdSet()
        
        ExampleBuilder.__init__(self, classSet, featureSet)
        assert( classSet.getId("neg") == 1 )
        #gazetteerFileName="/usr/share/biotext/GeniaChallenge/SharedTaskTriggerTest/gazetteer-train"
        if gazetteerFileName!=None:
            self.gazetteer=Gazetteer.loadGztr(gazetteerFileName)
            print >> sys.stderr, "Loaded gazetteer from",gazetteerFileName
        else:
            print >> sys.stderr, "No gazetteer loaded"
            self.gazetteer=None
        self._setDefaultParameters(["rel_features", "wordnet", "bb_features", "giuliano", 
                                  "epi_merge_negated", "limit_merged_types", "genia_task1",
                                  "build_for_nameless", "pos_only", "all_tokens",
                                  "names", "pos_pairs", "linear_ngrams", "phospho", 
                                  "drugbank_features", "ddi13_features", "metamap"])
        self.styles = self.getParameters(style)
#        if "selftrain_group" in self.styles:
#            self.selfTrainGroups = set()
#            if "selftrain_group-1" in self.styles:
#                self.selfTrainGroups.add("-1")
#            if "selftrain_group0" in self.styles:
#                self.selfTrainGroups.add("0")
#            if "selftrain_group1" in self.styles:
#                self.selfTrainGroups.add("1")
#            if "selftrain_group2" in self.styles:
#                self.selfTrainGroups.add("2")
#            if "selftrain_group3" in self.styles:
#                self.selfTrainGroups.add("3")
#            print >> sys.stderr, "Self-train-groups:", self.selfTrainGroups
        
        self.skiplist = set()
        if skiplist != None:
            f = open(skiplist, "rt")
            for line in f.readlines():
                self.skiplist.add(line.strip())
            f.close()
        
        if self.styles["rel_features"]:
            self.relFeatureBuilder = RELFeatureBuilder(featureSet)
        if self.styles["wordnet"]:
            self.wordNetFeatureBuilder = WordNetFeatureBuilder(featureSet)
        if self.styles["bb_features"]:
            self.bacteriaTokens = PhraseTriggerExampleBuilder.getBacteriaTokens()
            #self.bacteriaTokens = PhraseTriggerExampleBuilder.getBacteriaTokens(PhraseTriggerExampleBuilder.getBacteriaNames())
        if self.styles["giuliano"]:
            self.giulianoFeatureBuilder = GiulianoFeatureBuilder(featureSet)
        if self.styles["drugbank_features"]:
            self.drugFeatureBuilder = DrugFeatureBuilder(featureSet)
    
    def getMergedEntityType(self, entities):
        """
        If a single token belongs to multiple entities of different types,
        a new, composite type is defined. This type is the alphabetically
        ordered types of these entities joined with '---'.
        """
        types = set()
        entityIds = set()
        for entity in entities:
            if entity.get("given") == "True" and self.styles["all_tokens"]:
                continue
            if entity.get("type") == "Entity" and self.styles["genia_task1"]:
                continue
            if self.styles["epi_merge_negated"]:
                types.add(Utils.InteractionXML.ResolveEPITriggerTypes.getEPIBaseType(entity.get("type")))
                entityIds.add(entity.get("id"))
            else:
                types.add(entity.get("type"))
                entityIds.add(entity.get("id"))
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
            return "neg", None
        
        idString = "/".join(sorted(list(entityIds)))
        
        if self.styles["limit_merged_types"]:
            if typeString.find("---") != -1:
                if typeString == "Gene_expression---Positive_regulation":
                    return typeString, idString
                else:
                    return typeString.split("---")[0], idString # ids partially incorrect
            else:
                return typeString, idString
        return typeString, idString
    
    def getMetaMapFeatures(self, token, sentenceGraph, features):
        analyses = sentenceGraph.sentenceElement.find("analyses")
        if analyses == None:
            return
        metamap = analyses.find("metamap")
        if metamap == None:
            return
        tokenOffset = Range.charOffsetToSingleTuple(token.get("charOffset"))
        skipAttr = set(["charOffset", "text"])
        for phrase in metamap.findall("phrase"):
            phraseOffset = Range.charOffsetToSingleTuple(phrase.get("charOffset"))
            if Range.overlap(tokenOffset, phraseOffset):
                attr = phrase.attrib
                attrNames = sorted(attr.keys())
                for attrName in attrNames:
                    if attrName in skipAttr:
                        continue
                    elif attrName == "score":
                        features["_metamap_score"] = 0.001 * abs(int(attr[attrName]))
                    else:
                        attrValues = attr[attrName].split(",")
                        for attrValue in attrValues: 
                            features["_metamap_"+attrName+"_"+attrValue.replace(" ", "-")] = 1
    
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
        if sentenceGraph.tokenIsName[token] and not self.styles["names"]:
            features["_given"]=1
            for entity in sentenceGraph.tokenIsEntityHead[token]:
                if entity.get("given") == "True":
                    features["_annType_"+entity.get("type")]=1
        if self.styles["metamap"]:
            self.getMetaMapFeatures(token, sentenceGraph, features)
#        # Filip's gazetteer based features (can be used separately from exclude_gazetteer)
#        if "gazetteer_features" in self.styles:
#            tokTxtLower = tokTxt.lower()
#            if "stem_gazetteer" in self.styles:
#                tokTxtLower = PorterStemmer.stem(tokTxtLower)
#            if self.gazetteer and tokTxtLower in self.gazetteer:
#                for label,weight in self.gazetteer[tokTxtLower].items():
#                    features["_knownLabel_"+label]=weight # 1 performs slightly worse
        ## BANNER features
        #if sentenceGraph.entityHintsByToken.has_key(token):
        #    features["BANNER-entity"] = 1
        # Wordnet features
        #if "wordnet" in self.styles:
        #    for wordNetFeature in self.wordNetFeatureBuilder.getTokenFeatures(tokTxt, token.get("POS")):
        #        features["_WN_"+wordNetFeature] = 1
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
    
    def buildExamplesFromGraph(self, sentenceGraph, outfile, goldGraph=None, structureAnalyzer=None):
        """
        Build one example for each token of the sentence
        """       
        if sentenceGraph.sentenceElement.get("origId") in self.skiplist:
            print >> sys.stderr, "Skipping sentence", sentenceGraph.sentenceElement.get("origId") 
            return 0 #[]
        
        #examples = []
        exampleIndex = 0
        
        self.tokenFeatures = {}
        self.tokenFeatureWeights = {}
        
        namedEntityHeadTokens = []
        if not self.styles["names"]:
            namedEntityCount = 0
            for entity in sentenceGraph.entities:
                if entity.get("given") == "True": # known data which can be used for features
                    namedEntityCount += 1
            namedEntityCountFeature = "nameCount_" + str(namedEntityCount)
            # NOTE!!! This will change the number of examples and omit
            # all triggers (positive and negative) from sentences which
            # have no NE:s, possibly giving a too-optimistic performance
            # value. Such sentences can still have triggers from intersentence
            # interactions, but as such events cannot be recovered anyway,
            # looking for these triggers would be pointless.
            if namedEntityCount == 0 and not self.styles["build_for_nameless"]: # no names, no need for triggers
                return 0 #[]
            
            if self.styles["pos_pairs"]:
                namedEntityHeadTokens = self.getNamedEntityHeadTokens(sentenceGraph)
        else:
            for key in sentenceGraph.tokenIsName.keys():
                sentenceGraph.tokenIsName[key] = False
        
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
                categoryName, entityIds = self.getMergedEntityType(sentenceGraph.tokenIsEntityHead[token])
            else:
                categoryName, entityIds = "neg", None
            self.exampleStats.beginExample(categoryName)
            
            # Recognize only non-named entities (i.e. interaction words)
            if sentenceGraph.tokenIsName[token] and not self.styles["names"] and not self.styles["all_tokens"]:
                self.exampleStats.filter("name")
                self.exampleStats.endExample()
                continue
#            if "selftrain_limits" in self.styles:
#                # any predicted entity not part of the self-training set causes example to be rejected
#                filtered = False
#                for entity in sentenceGraph.tokenIsEntityHead[token]:
#                    if entity.get("selftrain") == "False":
#                        self.exampleStats.filter("selftrain_limits")
#                        self.exampleStats.endExample()
#                        filtered = True
#                        break
#                if filtered:
#                    continue
#            if "selftrain_group" in self.styles:
#                # any predicted entity not part of the self-training set causes example to be rejected
#                filtered = False
#                for entity in sentenceGraph.tokenIsEntityHead[token]:
#                    if entity.get("selftraingroup") not in self.selfTrainGroups:
#                        self.exampleStats.filter("selftrain_group")
#                        self.exampleStats.endExample()
#                        filtered = True
#                        break
#                if filtered:
#                    continue
            if self.styles["pos_only"] and categoryName == "neg":
                self.exampleStats.filter("pos_only")
                self.exampleStats.endExample()
                continue

            category = self.classSet.getId(categoryName)
            if category == None:
                self.exampleStats.filter("undefined_class")
                self.exampleStats.endExample()
                continue           
            
            tokenText = token.get("text").lower()
#            if "stem_gazetteer" in self.styles:
#                tokenText = PorterStemmer.stem(tokenText)
#            if ("exclude_gazetteer" in self.styles) and self.gazetteer and tokenText not in self.gazetteer:
#                features = {}
#                features[self.featureSet.getId("exclude_gazetteer")] = 1
#                extra = {"xtype":"token","t":token.get("id"),"excluded":"True"}
#                if entityIds != None:
#                    extra["goldIds"] = entityIds
#                #examples.append( (sentenceGraph.getSentenceId()+".x"+str(exampleIndex),category,features,extra) )
#                ExampleUtils.appendExamples([(sentenceGraph.getSentenceId()+".x"+str(exampleIndex),category,features,extra)], outfile)
#                exampleIndex += 1
#                continue
            
            # FEATURES
            features = {}
            
            if not self.styles["names"]:
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
            
            ## Subspan features
            #textLower = text.lower()
            #for i in range(1, len(textLower)):
            #    features[self.featureSet.getId("subspanbegin"+str(i)+"_"+textLower[0:i])] = 1
            #    features[self.featureSet.getId("subspanend"+str(i)+"_"+textLower[-i:])] = 1
            
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
            if self.styles["linear_ngrams"]:
                self.buildLinearNGram(max(0, i-1), i, sentenceGraph, features)
                self.buildLinearNGram(max(0, i-2), i, sentenceGraph, features)
            
            if self.styles["phospho"]:
                if text.find("hospho") != -1:
                    features[self.featureSet.getId("phospho_found")] = 1
                features[self.featureSet.getId("begin_"+text[0:2].lower())] = 1
                features[self.featureSet.getId("begin_"+text[0:3].lower())] = 1
                
            if self.styles["bb_features"]:
                if text.lower() in self.bacteriaTokens:
                    features[self.featureSet.getId("lpsnBacToken")] = 1

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
            if self.styles["rel_features"]:
                self.relFeatureBuilder.setFeatureVector(features)
                self.relFeatureBuilder.buildAllFeatures(sentenceGraph.tokens, i)
                self.relFeatureBuilder.setFeatureVector(None)
            
            # DDI13 features
            if self.styles["ddi13_features"]:
                for index in range(len(normalizedText)):
                    features[self.featureSet.getId("ddi13_fromstart" + str(index) + "_" + normalizedText[:index+1])] = 1
                    features[self.featureSet.getId("ddi13_fromend" + str(index) + "_" + normalizedText[index:])] = 1
            if self.styles["drugbank_features"]:
                self.drugFeatureBuilder.setFeatureVector(features)
                self.drugFeatureBuilder.tag = "ddi_"
                self.drugFeatureBuilder.buildDrugFeatures(token)  
                self.drugFeatureBuilder.setFeatureVector(None)
            
            #self.wordNetFeatureBuilder.getTokenFeatures("show", "VBP")
            #tokTxt = token.get("text")
            #tokPOS = token.get("POS")
            #wordNetFeatures = []
            #wordNetFeatures = self.wordNetFeatureBuilder.getTokenFeatures(tokTxt, tokPOS)
            #self.wordNetFeatureBuilder.getTokenFeatures(tokTxt, tokPOS)
            if self.styles["wordnet"]:
                tokTxt = token.get("text")
                tokPOS = token.get("POS")
                wordNetFeatures = self.wordNetFeatureBuilder.getTokenFeatures(tokTxt, tokPOS)
                for wordNetFeature in wordNetFeatures:
                    #print wordNetFeature,
                    features[self.featureSet.getId("WN_"+wordNetFeature)] = 1
                #print
            
            if self.styles["giuliano"]:
                self.giulianoFeatureBuilder.setFeatureVector(features)
                self.giulianoFeatureBuilder.buildTriggerFeatures(token, sentenceGraph)
                self.giulianoFeatureBuilder.setFeatureVector(None)
                             
            extra = {"xtype":"token","t":token.get("id")}
            if self.styles["bb_features"]:
                extra["trigex"] = "bb" # Request trigger extension in ExampleWriter
            if self.styles["epi_merge_negated"]:
                extra["unmergeneg"] = "epi" # Request trigger type unmerging
            if entityIds != None:
                extra["goldIds"] = entityIds # The entities to which this example corresponds
            #examples.append( (sentenceGraph.getSentenceId()+".x"+str(exampleIndex),category,features,extra) )
            
            # chains
            self.buildChains(token, sentenceGraph, features)
            
            if self.styles["pos_pairs"]:
                self.buildPOSPairs(token, namedEntityHeadTokens, features)
            
            example = (sentenceGraph.getSentenceId()+".x"+str(exampleIndex), category, features, extra)
            ExampleUtils.appendExamples([example], outfile)
            exampleIndex += 1
            self.exampleStats.endExample()
        #return examples
        return exampleIndex
    
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
#                    if entity.get("given") == "True":
#                        features[self.featureSet.getId("name_dist_"+strDepthLeft)] = 1
#                        features[self.featureSet.getId("name_dist_"+strDepthLeft+entity.get("type"))] = 1
#                features[self.featureSet.getId("POS_dist_"+strDepthLeft+nextToken.get("POS"))] = 1
#                tokenText = sentenceGraph.getTokenText(nextToken)
#                features[self.featureSet.getId("text_dist_"+strDepthLeft+tokenText)] = 1
                
                if sentenceGraph.tokenIsName[nextToken] and not self.styles["names"]:
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
#                    if entity.get("given") == "True":
#                        features[self.featureSet.getId("name_dist_"+strDepthLeft)] = 1
#                        features[self.featureSet.getId("name_dist_"+strDepthLeft+entity.get("type"))] = 1
#                features[self.featureSet.getId("POS_dist_"+strDepthLeft+nextToken.get("POS"))] = 1
#                tokenText = sentenceGraph.getTokenText(nextToken)
#                features[self.featureSet.getId("text_dist_"+strDepthLeft+tokenText)] = 1
                if sentenceGraph.tokenIsName[nextToken] and not self.styles["names"]:
                    features[self.featureSet.getId("name_chain_dist_"+strDepthLeft+chain+"-rev_"+edgeType)] = 1
                
                features[self.featureSet.getId("chain_dist_"+strDepthLeft+chain+"-rev_"+edgeType)] = 1
                self.buildChains(nextToken,sentenceGraph,features,depthLeft-1,chain+"-rev_"+edgeType,edgeSet)
    
    def getNamedEntityHeadTokens(self, sentenceGraph):
        headTokens = []
        for entity in sentenceGraph.entities:
            if entity.get("given") == "True": # known data which can be used for features
                headTokens.append(sentenceGraph.entityHeadTokenByEntity[entity])
        return headTokens
                
    def buildPOSPairs(self, token, namedEntityHeadTokens, features):
        tokenPOS = token.get("POS")
        assert tokenPOS != None
        for headToken in namedEntityHeadTokens:
            headPOS = headToken.get("POS")
            features[self.featureSet.getId("POS_pair_NE_"+tokenPOS+"-"+headPOS)] = 1
