"""
Trigger examples
"""
__version__ = "$Revision: 1.1 $"

import sys, os
thisPath = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(thisPath,"..")))
import Core.ExampleBuilder
from Core.ExampleBuilder import ExampleBuilder
import Stemming.PorterStemmer as PorterStemmer
from Core.IdSet import IdSet
import Core.ExampleUtils as ExampleUtils
from Core.Gazetteer import Gazetteer
import Graph.networkx_v10rc1 as NX10
from Utils.ProgressCounter import ProgressCounter
import combine
import cElementTreeUtils as ETUtils
from FeatureBuilders.MultiEdgeFeatureBuilder import MultiEdgeFeatureBuilder
from FeatureBuilders.TriggerFeatureBuilder import TriggerFeatureBuilder

def compareDependencyEdgesById(dep1, dep2):
    """
    Dependency edges are sorted, so that the program behaves consistently
    on the sama data between different runs.
    """
    id1 = dep1[2].get("id")
    id2 = dep2[2].get("id")
    if id1 > id2:
       return 1
    elif id1 == id2:
       return 0
    else: # x<y
       return -1

def compareInteractionPrecedence(e1, e2):
    """
    e1/e2 = (interaction, pathdist, lindist, tok2pos)
    """
    if e1[1] > e2[1]:
        return 1
    elif e1[1] < e2[1]:
        return -1
    else: # same dependency distance
        if e1[2] > e2[2]:
            return 1
        elif e1[2] < e2[2]:
            return -1
        else: # same linear distance
            if e1[3] > e2[3]:
                return 1
            elif e1[3] < e2[3]:
                return -1
            else: # same head token for entity 2
                return 0
                #assert False, ("Precedence error",e1,e2)

class Round2TriggerExampleBuilder(ExampleBuilder):
    def nxMultiDiGraphToUndirected(self, graph):
        undirected = NX10.MultiGraph(name=graph.name)
        undirected.add_nodes_from(graph)
        undirected.add_edges_from(graph.edges_iter())
        return undirected
    
    def getPredictionStrength(self, element):
        eType = element.get("type")
        predictions = element.get("predictions")
        if predictions == None:
            return 0
        predictions = predictions.split(",")
        for prediction in predictions:
            predClass, predStrength = prediction.split(":")
            if predClass == eType:
                predStrength = float(predStrength)
                return predStrength
        return 0
    
    def getInteractionEdgeLengths(self, sentenceGraph, paths):
        """
        Return dependency and linear length of all interaction edges
        (measured between the two tokens).
        """
        interactionLengths = {}
        for interaction in sentenceGraph.interactions:
            # Calculated interaction edge dep and lin length
            e1 = sentenceGraph.entitiesById[interaction.get("e1")]
            e2 = sentenceGraph.entitiesById[interaction.get("e2")]
            t1 = sentenceGraph.entityHeadTokenByEntity[e1]
            t2 = sentenceGraph.entityHeadTokenByEntity[e2]
            # Get dep path length
            if t1 != t2 and paths.has_key(t1) and paths[t1].has_key(t2):
                pathLength = len(paths[t1][t2])
            else: # no dependencyPath
                pathLength = 999999 # more than any real path
            # Linear distance
            t1Pos = -1
            t2Pos = -1
            for i in range(len(sentenceGraph.tokens)):
                if sentenceGraph.tokens[i] == t1:
                    t1Pos = i
                    if t2Pos != -1:
                        break
                if sentenceGraph.tokens[i] == t2:
                    t2Pos = i
                    if t1Pos != -1:
                        break
            linLength = abs(t1Pos - t2Pos)
            interactionLengths[interaction] = (interaction, pathLength, linLength, t2Pos)
        return interactionLengths

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

        self.styles = ["trigger_features","typed","directed","no_linear","entities","genia_limits","noMasking","maxFeatures"]
        self.multiEdgeFeatureBuilder = MultiEdgeFeatureBuilder(self.featureSet)
        if "graph_kernel" in self.styles:
            from FeatureBuilders.GraphKernelFeatureBuilder import GraphKernelFeatureBuilder
            self.graphKernelFeatureBuilder = GraphKernelFeatureBuilder(self.featureSet)
        if "noAnnType" in self.styles:
            self.multiEdgeFeatureBuilder.noAnnType = True
        if "noMasking" in self.styles:
            self.multiEdgeFeatureBuilder.maskNamedEntities = False
        if "maxFeatures" in self.styles:
            self.multiEdgeFeatureBuilder.maximum = True

        self.triggerFeatureBuilder = TriggerFeatureBuilder(self.featureSet)

    @classmethod
    def run(cls, input, gold, output, parse, tokenization, style, idFileTag=None, append=False):
        """
        An interface for running the example builder without needing to create a class
        """
        classSet, featureSet = cls.getIdSets(idFileTag)
        if style != None:
            e = Round2TriggerExampleBuilder(style=style, classSet=classSet, featureSet=featureSet)
        else:
            e = Round2TriggerExampleBuilder(classSet=classSet, featureSet=featureSet)
        sentences = cls.getSentences(input, parse, tokenization)
        if gold != None:
            goldSentences = cls.getSentences(gold, parse, tokenization)
        else:
            goldSentences = None
        e.buildExamplesForSentences(sentences, goldSentences, output, idFileTag, append=append)

    def buildExamplesForSentences(self, sentences, goldSentences, output, idFileTag=None, append=False):            
        examples = []
        counter = ProgressCounter(len(sentences), "Build examples")
        
        if append:
            outfile = open(output, "at")
        else:
            outfile = open(output, "wt")
        exampleCount = 0
        for i in range(len(sentences)):
            sentence = sentences[i]
            goldSentence = [None]
            if goldSentences != None:
                goldSentence = goldSentences[i]
            counter.update(1, "Building examples ("+sentence[0].getSentenceId()+"): ")
            examples = self.buildExamples(sentence[0], goldSentence[0], append=append)
            exampleCount += len(examples)
            examples = self.preProcessExamples(examples)
            ExampleUtils.appendExamples(examples, outfile)
        outfile.close()
    
        print >> sys.stderr, "Examples built:", exampleCount
        print >> sys.stderr, "Features:", len(self.featureSet.getNames())
        #IF LOCAL
        if self.exampleStats.getExampleCount() > 0:
            self.exampleStats.printStats()
        #ENDIF
        # Save Ids
        if idFileTag != None: 
            print >> sys.stderr, "Saving class names to", idFileTag + ".class_names"
            self.classSet.write(idFileTag + ".class_names")
            print >> sys.stderr, "Saving feature names to", idFileTag + ".feature_names"
            self.featureSet.write(idFileTag + ".feature_names")

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
            types.add(entity.get("type"))
        types = list(types)
        types.sort()
        typeString = ""
        for type in types:
            if type == "Protein" and "all_tokens" in self.styles:
                continue
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
            return self.tokenFeatures[token]
        tokTxt=sentenceGraph.getTokenText(token)
        features = {}
        features["_txt_"+tokTxt]=1
        
        # F 69.35 -> 68.22
        #normalizedText = tokTxt.replace("-","").replace("/","").replace(",","").replace("\\","").replace(" ","").lower()
        #features["_norTxt_"+normalizedText]=1
        #features["_norStem_" + PorterStemmer.stem(normalizedText)]=1
        
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
        self.tokenFeatures[token] = features
        return features
    
    def buildLinearOrderFeatures(self,sentenceGraph,index,tag,features):
        """
        Linear features are built by marking token features with a tag
        that defines their relative position in the linear order.
        """
        tag = "linear_"+tag
        for tokenFeature,w in self.getTokenFeatures(sentenceGraph.tokens[index], sentenceGraph).iteritems():
            features[self.featureSet.getId(tag+tokenFeature)] = w
    
    def buildExamples(self, sentenceGraph, goldGraph, append=False):
        examples = self.buildExamplesInner(sentenceGraph, goldGraph)
        
        entityCounts = {}
        exampleCounts = {}
        for entity in sentenceGraph.entities:
            eType = entity.get("type")
            if eType == "Protein":
                continue
            if not entityCounts.has_key(eType):
                entityCounts[eType] = 0
                exampleCounts[eType] = 0
            entityCounts[eType] += 1
        
        for example in examples:
            eTypes = self.classSet.getName(example[1]).split("---")
            for eType in eTypes:
                if not exampleCounts.has_key(eType):
                    exampleCounts[eType] = 0
                exampleCounts[eType] += 1
        #for key in sorted(entityCounts.keys()):
        #    if entityCounts[key] != exampleCounts[key]:
        #        print >> sys.stderr, "Warning, sentence", sentenceGraph.getSentenceId(), "example", key, "diff", entityCounts[key] - exampleCounts[key]  
        
        return examples
    
    def buildExamplesInner(self, sentenceGraph, goldGraph):
        """
        Build one example for each token of the sentence
        """
        if sentenceGraph.sentenceElement.get("origId") in self.skiplist:
            print >> sys.stderr, "Skipping sentence", sentenceGraph.sentenceElement.get("origId") 
            return []

        self.multiEdgeFeatureBuilder.setFeatureVector(resetCache=True)
        self.triggerFeatureBuilder.initSentence(sentenceGraph)

        undirected = self.nxMultiDiGraphToUndirected(sentenceGraph.dependencyGraph)
        paths = NX10.all_pairs_shortest_path(undirected, cutoff=999)
        # Get argument order
        self.interactionLengths = self.getInteractionEdgeLengths(sentenceGraph, paths)        
        self.interactionLengths = self.interactionLengths.values()
        self.interactionLengths.sort(compareInteractionPrecedence)
        # Map tokens to entities
        tokenByOffset = {}
        for i in range(len(sentenceGraph.tokens)):
            token = sentenceGraph.tokens[i]
            if goldGraph != None:
                goldToken = goldGraph.tokens[i]
                assert token.get("id") == goldToken.get("id") and token.get("charOffset") == goldToken.get("charOffset")
            tokenByOffset[token.get("charOffset")] = token.get("id")
        # Map gold entities to their head offsets
        goldEntitiesByOffset = {}
        for token in sentenceGraph.tokens:
            goldEntitiesByOffset[token.get("charOffset")] = []
        entityToGold = {}
        for entity in sentenceGraph.entities:
            entityToGold[entity] = []
        if goldGraph != None:
            for entity in goldGraph.entities:
                offset = entity.get("headOffset")
                assert offset != None
                goldEntitiesByOffset[offset].append(entity)
            # Map predicted entities to gold entities
            for entity in sentenceGraph.entities:
                eType = entity.get("type")
                eOffset = entity.get("headOffset")
                for goldEntity in goldEntitiesByOffset[eOffset]:
                    if goldEntity.get("type") == eType:
                        entityToGold[entity].append(goldEntity)
        # Map entities to interactions
        #interactionsByEntityId = {}
        #for entity in sentenceGraph.entities:
        #    interactionsByEntityId[entity.get("id")] = []
        # Map tokens to interactions
        interactionsByToken = {}
        for token in sentenceGraph.tokens:
            interactionsByToken[token] = []
        for interactionTuple in self.interactionLengths:
            interaction = interactionTuple[0]
            if interaction.get("type") == "neg":
                continue
            e1Id = interaction.get("e1")
            token = sentenceGraph.entityHeadTokenByEntity[sentenceGraph.entitiesById[e1Id]]
            interactionsByToken[token].append(interaction)
        
        examples = []
        exampleIndex = 0
        
        self.tokenFeatures = {}
        
        #namedEntityNorStrings = set()
        namedEntityHeadTokens = []
        if not "names" in self.styles:
            namedEntityCount = 0
            for entity in sentenceGraph.entities:
                if entity.get("isName") == "True": # known data which can be used for features
                    namedEntityCount += 1
                    #namedEntityNorStrings.add( entity.get("text").replace("-","").replace("/","").replace(",","").replace("\\","").replace(" ","").lower() )
            namedEntityCountFeature = "nameCount_" + str(namedEntityCount)
            #if namedEntityCount == 0: # no names, no need for triggers
            #    return []
            
            if "pos_pairs" in self.styles:
                namedEntityHeadTokens = self.getNamedEntityHeadTokens(sentenceGraph)
        
        #neFeatures = {} # F: 69.35 -> 69.14
        #for norString in namedEntityNorStrings:
        #    neFeatures[self.featureSet.getId("norNE_" + norString)] = 1
        
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
        for k,v in bagOfWords.iteritems():
            bowFeatures[self.featureSet.getId(k)] = v
        
        self.inEdgesByToken = {}
        self.outEdgesByToken = {}
        self.edgeSetByToken = {}
        for token in sentenceGraph.tokens:
            inEdges = sentenceGraph.dependencyGraph.in_edges(token, data=True)
            fixedInEdges = []
            for edge in inEdges:
                fixedInEdges.append( (edge[0], edge[1], edge[2]["element"]) )
            inEdges = fixedInEdges
            inEdges.sort(compareDependencyEdgesById)
            self.inEdgesByToken[token] = inEdges
            outEdges = sentenceGraph.dependencyGraph.out_edges(token, data=True)
            fixedOutEdges = []
            for edge in outEdges:
                fixedOutEdges.append( (edge[0], edge[1], edge[2]["element"]) )
            outEdges = fixedOutEdges
            outEdges.sort(compareDependencyEdgesById)
            self.outEdgesByToken[token] = outEdges
            self.edgeSetByToken[token] = set(inEdges + outEdges)
        
        for i in range(len(sentenceGraph.tokens)):
            token = sentenceGraph.tokens[i]
            # Recognize only non-named entities (i.e. interaction words)
            if sentenceGraph.tokenIsName[token] and not "names" in self.styles and not "all_tokens" in self.styles:
                continue

            # CLASS
            #if len(sentenceGraph.tokenIsEntityHead[token]) > 0:
            #    category = self.classSet.getId(self.getMergedEntityType(sentenceGraph.tokenIsEntityHead[token]))
            #else:
            #    category = 1
            offset = token.get("charOffset")
            if len(goldEntitiesByOffset[offset]) > 0:
                category = self.classSet.getId(self.getMergedEntityType(goldEntitiesByOffset[offset]))
            else:
                category = 1
            
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
            self.features = features
            
            
            
            if not "names" in self.styles:
                features[self.featureSet.getId(namedEntityCountFeature)] = 1
            #for k,v in bagOfWords.iteritems():
            #    features[self.featureSet.getId(k)] = v
            # pre-calculate bow _features_
            features.update(bowFeatures)
            #features.update(neFeatures)
            
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
            
            if "gazetteer_features_maintoken" in self.styles:
                tokTxtLower = text.lower()
                if "stem_gazetteer" in self.styles:
                    tokTxtLower = PorterStemmer.stem(tokTxtLower)
                if self.gazetteer and tokTxtLower in self.gazetteer:
                    for label,weight in self.gazetteer[tokTxtLower].items():
                        features[self.featureSet.getId("gaz_knownLabel_"+label)]=weight # 1 performs slightly worse
                
            
            # Linear order features
            #for index in [-3,-2,-1,1,2,3,4,5]: # 69.35 -> 68.97
            for index in [-3,-2,-1,1,2,3]:
                if i + index > 0 and i + index < len(sentenceGraph.tokens):
                    self.buildLinearOrderFeatures(sentenceGraph, i + index, str(index), features)
            
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
            t1OutEdges = self.outEdgesByToken[token]
            for edge in t1OutEdges:
                edgeType = edge[2].get("type")
                features[self.featureSet.getId("t1HOut_"+edgeType)] = 1
                features[self.featureSet.getId("t1HOut_"+edge[1].get("POS"))] = 1
                features[self.featureSet.getId("t1HOut_"+edgeType+"_"+edge[1].get("POS"))] = 1
                tokenText = sentenceGraph.getTokenText(edge[1])
                features[self.featureSet.getId("t1HOut_"+tokenText)] = 1
                features[self.featureSet.getId("t1HOut_"+edgeType+"_"+tokenText)] = 1
             
            extra = {"xtype":"token","t":token.get("id")}
            examples.append( (sentenceGraph.getSentenceId()+".x"+str(exampleIndex),category,features,extra) )
            exampleIndex += 1
            
            # chains
            self.buildChains(token, sentenceGraph, features)
            
            if "pos_pairs" in self.styles:
                self.buildPOSPairs(token, namedEntityHeadTokens, features)
            
            self.buildPredictionFeatures(sentenceGraph, paths, token, interactionsByToken[token])   
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
                for tokenFeature,w in self.getTokenFeatures(nextToken, sentenceGraph).iteritems():
                    features[self.featureSet.getId(strDepthLeft + tokenFeature)] = w
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
                for tokenFeature,w in self.getTokenFeatures(nextToken, sentenceGraph).iteritems():
                    features[self.featureSet.getId(strDepthLeft + tokenFeature)] = w
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
    
    ######################################################
    # Unmerging-style features
    ######################################################

    def buildPredictionFeatures(self, sentenceGraph, paths, token, interactions): #themeEntities, causeEntities=None):
        # NOTE!!!! TODO
        # add also features for arguments present, but not in this combination
        
        self.buildInterArgumentBagOfWords(interactions, sentenceGraph)
        
        if sentenceGraph.entitiesByToken.has_key(token):
            for eventEntity in sentenceGraph.entitiesByToken[token]:
                eventEntityType = eventEntity.get("type")
                self.setFeature("rootType_"+eventEntity.get("type"), 1)
                self.setFeature("predStrength"+eventEntityType, self.getPredictionStrength(eventEntity))
                self.triggerFeatureBuilder.setFeatureVector(self.features)
                self.triggerFeatureBuilder.tag = "trg" + eventEntityType + "_"
                self.triggerFeatureBuilder.buildFeatures(token)
                self.triggerFeatureBuilder.tag = None
        
        argThemeCount = 0
        argCauseCount = 0
        # Current example's edge combination
        for i in range(len(interactions)):
            arg = interactions[i]
            if arg.get("type") == "Theme":
                argThemeCount += 1
                self.buildArgumentFeatures(sentenceGraph, paths, self.features, token, arg, "argTheme")
                self.buildArgumentFeatures(sentenceGraph, paths, self.features, token, arg, "argTheme"+str(i))
            else: # Cause
                argCauseCount += 1
                self.buildArgumentFeatures(sentenceGraph, paths, self.features, token, arg, "argCause")
                self.buildArgumentFeatures(sentenceGraph, paths, self.features, token, arg, "argCause"+str(i))
        
        self.setFeature("argCount", len(interactions))
        self.setFeature("argCount_" + str(len(interactions)), 1)
        
        self.setFeature("argThemeCount", argThemeCount)
        self.setFeature("argThemeCount_" + str(argThemeCount), 1)
        self.setFeature("argCauseCount", argCauseCount)
        self.setFeature("argCauseCount_" + str(argCauseCount), 1)
        
        self.triggerFeatureBuilder.tag = ""
        self.triggerFeatureBuilder.setFeatureVector(None)

    def buildArgumentFeatures(self, sentenceGraph, paths, features, eventToken, arg, tag):
        argEntity = sentenceGraph.entitiesById[arg.get("e2")]
        argToken = sentenceGraph.entityHeadTokenByEntity[argEntity]
        self.buildEdgeFeatures(sentenceGraph, paths, features, eventToken, argToken, tag)
        self.triggerFeatureBuilder.tag = tag + "trg_"
        self.triggerFeatureBuilder.buildFeatures(argToken)
        if argEntity.get("isName") == "True":
            self.setFeature(tag+"Protein", 1)
        else:
            self.setFeature(tag+"Event", 1)
            self.setFeature("nestingEvent", 1)
        self.setFeature(tag+"_"+argEntity.get("type"), 1)
    
    def buildEdgeFeatures(self, sentenceGraph, paths, features, eventToken, argToken, tag):
        #eventToken = sentenceGraph.entityHeadTokenByEntity[eventNode]
        #argToken = sentenceGraph.entityHeadTokenByEntity[argNode]
        self.multiEdgeFeatureBuilder.tag = tag + "_"
        self.multiEdgeFeatureBuilder.setFeatureVector(features, None, None, False)
        
        self.setFeature(tag+"_present", 1)
        
        if eventToken != argToken and paths.has_key(eventToken) and paths[eventToken].has_key(argToken):
            path = paths[eventToken][argToken]
            edges = self.multiEdgeFeatureBuilder.getEdges(sentenceGraph.dependencyGraph, path)
        else:
            path = [eventToken, argToken]
            edges = None
        
        if not "disable_entity_features" in self.styles:
            self.multiEdgeFeatureBuilder.buildEntityFeatures(sentenceGraph)
        self.multiEdgeFeatureBuilder.buildPathLengthFeatures(path)
        #if not "disable_terminus_features" in self.styles:
        #    self.multiEdgeFeatureBuilder.buildTerminusTokenFeatures(path, sentenceGraph) # remove for fast
        if not "disable_single_element_features" in self.styles:
            self.multiEdgeFeatureBuilder.buildSingleElementFeatures(path, edges, sentenceGraph)
        if not "disable_ngram_features" in self.styles:
            self.multiEdgeFeatureBuilder.buildPathGrams(2, path, edges, sentenceGraph) # remove for fast
            self.multiEdgeFeatureBuilder.buildPathGrams(3, path, edges, sentenceGraph) # remove for fast
            self.multiEdgeFeatureBuilder.buildPathGrams(4, path, edges, sentenceGraph) # remove for fast
        if not "disable_path_edge_features" in self.styles:
            self.multiEdgeFeatureBuilder.buildPathEdgeFeatures(path, edges, sentenceGraph)
        #self.multiEdgeFeatureBuilder.buildSentenceFeatures(sentenceGraph)
        self.multiEdgeFeatureBuilder.setFeatureVector(None, None, None, False)
        self.multiEdgeFeatureBuilder.tag = ""
    
    def buildInterArgumentBagOfWords(self, arguments, sentenceGraph):
        if len(arguments) < 2:
            return

        indexByToken = {}
        for i in range(len(sentenceGraph.tokens)):
            indexByToken[sentenceGraph.tokens[i]] = i
        
        argTokenIndices = set()
        for arg in arguments:
            argEntity = sentenceGraph.entitiesById[arg.get("e2")]
            argToken = sentenceGraph.entityHeadTokenByEntity[argEntity]
            argTokenIndices.add(indexByToken[argToken])
        minIndex = min(argTokenIndices)
        maxIndex = max(argTokenIndices)
        self.setFeature("argBoWRange", (maxIndex-minIndex))
        self.setFeature("argBoWRange_" + str(maxIndex-minIndex), 1)
        bow = set()
        for i in range(minIndex+1, maxIndex):
            token = sentenceGraph.tokens[i]
            if len(sentenceGraph.tokenIsEntityHead[token]) == 0 and not sentenceGraph.tokenIsName[token]:
                bow.add(token.get("text"))
        bow = sorted(list(bow))
        for word in bow:
            self.setFeature("argBoW_"+word, 1)
            if word in ["/", "-"]:
                self.setFeature("argBoW_slashOrHyphen", 1)
        if len(bow) == 1:
            self.setFeature("argBoWonly_"+bow[0], 1)
            if bow[0] in ["/", "-"]:
                self.setFeature("argBoWonly_slashOrHyphen", 1)
