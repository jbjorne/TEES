__version__ = "$Revision: 1.5 $"

import sys, os
thisPath = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(thisPath,"..")))
import Core.ExampleBuilder
from Core.ExampleBuilder import ExampleBuilder
import Stemming.PorterStemmer as PorterStemmer
from Core.IdSet import IdSet
import Core.ExampleUtils as ExampleUtils
from Core.Gazetteer import Gazetteer

def readWords(filename):
    f = open(filename)
    words = set()
    for line in f.readlines():
        words.add(line.strip())
    stems = set()
    for word in words:
        stems.add(PorterStemmer.stem(word))
    return words, stems

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

class Task3ExampleBuilder(ExampleBuilder):
    def __init__(self, style=None, classSet=None, featureSet=None, gazetteerFileName=None):
        if classSet == None:
            classSet = IdSet(1)
        assert( classSet.getId("neg") == 1 )
        if featureSet == None:
            featureSet = IdSet()
        
        wordFilePath = os.path.abspath(os.path.join(thisPath,"../../data/speculation-words.txt"))
#IF LOCAL
        wordFilePath = "/usr/share/biotext/GeniaChallenge/extension-data/genia/task3/speculation-words.txt"    
#ENDIF        
        self.specWords, self.specWordStems = readWords(wordFilePath) 
        #print self.specWords
        #print self.specWordStems
        #sys.exit()
        
        ExampleBuilder.__init__(self, classSet, featureSet)
        #gazetteerFileName="/usr/share/biotext/GeniaChallenge/SharedTaskTriggerTest/gazetteer-train"
        if gazetteerFileName!=None:
            self.gazetteer=Gazetteer.loadGztr(gazetteerFileName)
            print >> sys.stderr, "Loaded gazetteer from",gazetteerFileName
        else:
            self.gazetteer=None
        self.styles = style

    @classmethod
    def run(cls, input, output, parse, tokenization, style, idFileTag=None, gazetteerFileName=None):
        classSet, featureSet = cls.getIdSets(idFileTag)
        e = Task3ExampleBuilder(style, classSet, featureSet, gazetteerFileName=None)
        sentences = cls.getSentences(input, parse, tokenization)
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
            return self.tokenFeatures[token]
        tokTxt=sentenceGraph.getTokenText(token)
        features = {}
        features["_txt_"+tokTxt]=1
        features["_POS_"+token.get("POS")]=1
        if "speculation" in self.styles: 
            if tokTxt in self.specWords:
                features["_spec"]=1
                features["_spec_"+tokTxt]=1
            tokStem = PorterStemmer.stem(tokTxt)
            if tokStem in self.specWordStems:
                features["_spec_stem"]=1
                features["_spec_stem_"+tokStem]=1
        if sentenceGraph.tokenIsName[token]:
            features["_isName"]=1
            for entity in sentenceGraph.tokenIsEntityHead[token]:
                if entity.get("isName") == "True":
                    features["_annType_"+entity.get("type")]=1
        if self.gazetteer and tokTxt.lower() in self.gazetteer:
            for label,weight in self.gazetteer[tokTxt.lower()].items():
                pass
                #features["_knownLabel_"+label]=weight
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
    
    def buildExamples(self, sentenceGraph):
        """
        Build one example for each token of the sentence
        """
        examples = []
        exampleIndex = 0
        
        self.tokenFeatures = {}
        
        namedEntityCount = 0
        entityCount = 0
        for entity in sentenceGraph.entities:
            if entity.get("isName") == "True": # known data which can be used for features
                namedEntityCount += 1
            else: # known data which can be used for features
                entityCount += 1
        namedEntityCountFeature = "nameCount_" + str(namedEntityCount)
        entityCountFeature = "entityCount_" + str(entityCount)
        
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
            if len(sentenceGraph.tokenIsEntityHead) > 0:
                text = "ge_" + text
                if not bagOfWords.has_key(text):
                    bagOfWords[text] = 0
                bagOfWords[text] += 1
            
            text = token.get("text")
            if "speculation" in self.styles and text in self.specWords:
                if not bagOfWords.has_key("spec_bow_"+text):
                    bagOfWords["spec_bow_"+text] = 0
                bagOfWords["spec_bow_"+text] += 1
                bagOfWords["spec_sentence"] = 1
        
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
        
        for entity in sentenceGraph.entities:
            #token = sentenceGraph.tokens[i]
            token = sentenceGraph.entityHeadTokenByEntity[entity]
            # Recognize only non-named entities (i.e. interaction words)
            if entity.get("isName") == "True":
                continue
            
            # CLASS
            if "speculation" in self.styles:
                task3Type = "speculation"
                if entity.get("speculation") == "True":
                    category = self.classSet.getId("speculation")
                else:
                    category = 1
            else:
                task3Type = "negation"
                if entity.get("negation") == "True":
                    category = self.classSet.getId("negation")
                else:
                    category = 1
                

            # FEATURES
            features = {}

            # ENTITY TYPE
            entityType = self.classSet.getId(self.getMergedEntityType(entity))
            features[self.featureSet.getId(entityType)] = 1
            
            features[self.featureSet.getId(namedEntityCountFeature)] = 1
            features[self.featureSet.getId(entityCountFeature)] = 1
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
            
            if "speculation" in self.styles:
                if text in self.specWords:
                    features[self.featureSet.getId("ent_spec")] = 1
                if stem in self.specWordStems:
                    features[self.featureSet.getId("ent_spec_stem")] = 1
            
            # Linear order features
            for i in range(len(sentenceGraph.tokens)):
                if token == sentenceGraph.tokens[i]:
                    break
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
             
            extra = {"xtype":"task3","t3type":task3Type,"t":token.get("id"),"entity":entity.get("id")}
            examples.append( (sentenceGraph.getSentenceId()+".x"+str(exampleIndex),category,features,extra) )
            exampleIndex += 1
            
            # chains
            self.buildChains(token, sentenceGraph, features)
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
                
                features[self.featureSet.getId("chain_dist_"+strDepthLeft+chain+"-frw_"+edgeType)] = 1
                self.buildChains(nextToken,sentenceGraph,features,depthLeft-1,chain+"-frw_"+edgeType,edgeSet)

        for edge in outEdges:
            if not edge in visited:
                edgeType = edge[2].get("type")
                features[self.featureSet.getId("dep_dist_"+strDepthLeft+edgeType)] = 1

                nextToken = edge[1]
                for tokenFeature,w in self.getTokenFeatures(nextToken, sentenceGraph).iteritems():
                    features[self.featureSet.getId(strDepthLeft + tokenFeature)] = w
                
                features[self.featureSet.getId("chain_dist_"+strDepthLeft+chain+"-rev_"+edgeType)] = 1
                self.buildChains(nextToken,sentenceGraph,features,depthLeft-1,chain+"-rev_"+edgeType,edgeSet)
