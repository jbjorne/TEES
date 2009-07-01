import sys
sys.path.append("..")
import Core.ExampleBuilder
from Core.ExampleBuilder import ExampleBuilder
import Stemming.PorterStemmer as PorterStemmer
from Core.IdSet import IdSet
import Core.ExampleUtils as ExampleUtils
import copy
from Utils.Timer import Timer
    
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


class GeneralEntityTypeRecognizer(ExampleBuilder):
    def __init__(self, style=None, classSet=None, featureSet=None):
        if classSet == None:
            classSet = IdSet(1)
        assert( classSet.getId("neg") == 1 )
        if featureSet == None:
            featureSet = IdSet()
        
        ExampleBuilder.__init__(self, classSet, featureSet)
        self.styles = style
        self.timerBuildExamples = Timer(False)
        self.timerCrawl = Timer(False)
        self.timerCrawlPrecalc = Timer(False)
        self.timerMatrix = Timer(False)
        self.timerMatrixPrecalc = Timer(False)
    
    @classmethod
    def run(cls, input, output, parse, tokenization, style, idFileTag=None):
        classSet, featureSet = cls.getIdSets(idFileTag)
        e = GeneralEntityTypeRecognizer(style, classSet, featureSet)
        sentences = cls.getSentences(input, parse, tokenization)
        e.buildExamplesForSentences(sentences, output, idFileTag)
        print >> sys.stderr, "Time for buildExamples:", e.timerBuildExamples.elapsedTimeToString()
        print >> sys.stderr, "Time for Crawl:", e.timerCrawl.elapsedTimeToString()
        print >> sys.stderr, "Time for Crawl(Precalc):", e.timerCrawlPrecalc.elapsedTimeToString()
        print >> sys.stderr, "Time for Matrix:", e.timerMatrix.elapsedTimeToString()
        print >> sys.stderr, "Time for Matrix(Precalc):", e.timerMatrixPrecalc.elapsedTimeToString()

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
        
        features = []
        features.append("_txt_"+sentenceGraph.getTokenText(token))
        features.append("_POS_"+token.get("POS"))
        if sentenceGraph.tokenIsName[token]:
            features.append("_isName")
            for entity in sentenceGraph.tokenIsEntityHead[token]:
                if entity.get("isName") == "True":
                    features.append("_annType_"+entity.get("type"))
        
        self.tokenFeatures[token] = features
        return features
    
    def buildLinearOrderFeatures(self,sentenceGraph,index,tag,features):
        """
        Linear features are built by marking token features with a tag
        that defines their relative position in the linear order.
        """
        tag = "linear_"+tag
        for tokenFeature in self.getTokenFeatures(sentenceGraph.tokens[index], sentenceGraph):
            features[self.featureSet.getId(tag+tokenFeature)] = 1
    
    def buildExamples(self, sentenceGraph):
        """
        Build one example for each token of the sentence
        """
        self.timerBuildExamples.start()
        examples = []
        exampleIndex = 0
        
        self.tokenFeatures = {}
        
        namedEntityCount = 0
        for entity in sentenceGraph.entities:
            if entity.get("isName") == "True": # known data which can be used for features
                namedEntityCount += 1
        namedEntityCountFeature = "nameCount_" + str(namedEntityCount)
        
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
        
        self.timerCrawl.start()
        self.timerCrawlPrecalc.start()
        self.inEdgesByToken = {}
        self.outEdgesByToken = {}
        self.edgeSetByToken = {}
        for token in sentenceGraph.tokens:
            inEdges = sentenceGraph.dependencyGraph.in_edges(token)
            inEdges.sort(compareDependencyEdgesById)
            self.inEdgesByToken[token] = inEdges
            outEdges = sentenceGraph.dependencyGraph.out_edges(token)
            outEdges.sort(compareDependencyEdgesById)
            self.outEdgesByToken[token] = outEdges
            self.edgeSetByToken[token] = set(inEdges + outEdges)
        self.timerCrawl.stop()
        self.timerCrawlPrecalc.stop()
        
        self.timerMatrix.start()
        self.timerMatrixPrecalc.start()
        self._initMatrices(sentenceGraph)
        self.timerMatrix.stop()
        self.timerMatrixPrecalc.stop()
        
        for i in range(len(sentenceGraph.tokens)):
            token = sentenceGraph.tokens[i]
            # Recognize only non-named entities (i.e. interaction words)
            if sentenceGraph.tokenIsName[token]:
                continue
            
            # CLASS
            if len(sentenceGraph.tokenIsEntityHead[token]) > 0:
                category = self.classSet.getId(self.getMergedEntityType(sentenceGraph.tokenIsEntityHead[token]))
            else:
                category = 1
            
            # FEATURES
            features = {}
            
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
            
            # Linear order features
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
            copyFeatures = copy.copy(features)
            self.timerCrawl.start()
            self.buildChains(token, sentenceGraph, features)
            self.timerCrawl.stop()
            self.timerMatrix.start()
            self.buildChainsAlternative(token, copyFeatures, sentenceGraph)
            self.timerMatrix.stop()
            diff1 = set(features.keys()) - set(copyFeatures.keys())
            diff2 = set(copyFeatures.keys()) - set(features.keys())
            if len(diff1) != 0 or len(diff2) != 0:
                print "Error for token", token.get("id"), token.get("text")
                intersection = set(features.keys()) & set(copyFeatures.keys())
                print "d1:",
                for key in sorted(diff1):
                    print self.featureSet.getName(key) + ",",
                print
                print "d2:",
                for key in sorted(diff2):
                    print self.featureSet.getName(key) + ",",
                print
                print "int:",
                intNames = []
                for key in sorted(intersection):
                    intNames.append(self.featureSet.getName(key))
                for name in sorted(intNames):
                    print name + ",",
                print
                #assert(len(diff1) == 0)
        self.timerBuildExamples.stop()
        return examples
    
    def _initMatrices(self, sentenceGraph):
        nodes = sentenceGraph.dependencyGraph.nodes()
        self.dod1 = self._dodFromGraph(sentenceGraph, nodes)
        self.dod2 = self.multDictOfDicts(self.dod1, self.dod1, nodes)
        self.dod3 = self.multDictOfDicts(self.dod2, self.dod1, nodes)
        #self.toStringMatrix(self.dod1)
        #self.toStringMatrix(self.dod2)
        #self.toStringMatrix(self.dod3)
            
    def _dodFromGraph(self, sentenceGraph, nodes):
        graph = sentenceGraph.dependencyGraph
        dod = {}
        for i in nodes:
            dod[i] = {}
        for i in nodes:
            for j in nodes:
                edge = graph.get_edge(i, j)
                if len(edge) > 0:
                    if not dod[i].has_key(j):
                        dod[i][j] = []
                    if not dod[j].has_key(i):
                        dod[j][i] = []
                    for e in edge:
                        t1 = sentenceGraph.tokensById[e.get("t1")]
                        t2 = sentenceGraph.tokensById[e.get("t2")]
                        # list of visited tokens, last edge of chain, chain string
                        dod[i][j].append( ([t1, t2], e, "frw_"+e.get("type")) ) # frw
                        dod[j][i].append( ([t2, t1], e, "rev_"+e.get("type")) ) # rev
        return dod

    def overlap(self, list1, list2):
        for i in list1:
            for j in list2:
                if i == j: # duplicate dependency
                    return True
        return False
    
    def extendPaths(self, edges1, edges2):
        newEdges = []
        for e1 in edges1:
            for e2 in edges2:
                if not self.overlap(e1[0], e2[0][1:]):
                    newEdges.append( (e1[0] + e2[0][1:], e2[1], e1[2] + "-" + e2[2]) )
        return newEdges

    def multDictOfDicts(self, dod1, dod2, nodes):
        result = {}
        for i in nodes:
            result[i] = {}
        for i in nodes:
            for j in nodes:
                for k in nodes:
                    if dod1[i].has_key(k):
                        edges1 = dod1[i][k]
                    else:
                        edges1 = []
                    if dod2[k].has_key(j):
                        edges2 = dod2[k][j]
                    else:
                        edges2 = []
                    newPaths = self.extendPaths(edges1, edges2)
                    if len(newPaths) > 0:
                        if result[i].has_key(j):
                            result[i][j].extend(newPaths)
                        else:
                            result[i][j] = newPaths
        return result

#    def toStringMatrix(self, matrix):
#        for i in matrix.keys():
#            for j in matrix[i].keys():
#                newList = []
#                for l in matrix[i][j]:
#                    string = ""
#                    for obj in l:
#                        if string != "":
#                            string += "-"
#                        if obj[1]:
#                            string += "frw_"+str(obj[0].get("type"))
#                        else:
#                            string += "rev_"+str(obj[0].get("type"))
#                    newList.append( (l, string) )
#                matrix[i][j] = newList
    
    def buildChainsAlternative(self, token, features, sentenceGraph):
        self._buildChainsMatrix(self.dod1, token, features, 3, sentenceGraph)
        self._buildChainsMatrix(self.dod2, token, features, 2, sentenceGraph)
        self._buildChainsMatrix(self.dod3, token, features, 1, sentenceGraph)
    
    def _buildChainsMatrix(self, matrix, token, features, depth, sentenceGraph):
        strDepthLeft = "dist_" + str(depth)
        for node in matrix[token].keys():
            if node == token: # don't allow self-loops
                continue
            for tokenFeature in self.getTokenFeatures(node, sentenceGraph):
                features[self.featureSet.getId(strDepthLeft + tokenFeature)] = 1
            for chain in matrix[token][node]:
                features[self.featureSet.getId("chain_"+strDepthLeft+"-"+chain[2])] = 1
                features[self.featureSet.getId("dep_"+strDepthLeft+chain[1].get("type"))] = 1
            
    
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
                for tokenFeature in self.getTokenFeatures(nextToken, sentenceGraph):
                    features[self.featureSet.getId(strDepthLeft + tokenFeature)] = 1
#                for entity in sentenceGraph.tokenIsEntityHead[nextToken]:
#                    if entity.get("isName") == "True":
#                        features[self.featureSet.getId("name_dist_"+strDepthLeft)] = 1
#                        features[self.featureSet.getId("name_dist_"+strDepthLeft+entity.get("type"))] = 1
#                features[self.featureSet.getId("POS_dist_"+strDepthLeft+nextToken.get("POS"))] = 1
#                tokenText = sentenceGraph.getTokenText(nextToken)
#                features[self.featureSet.getId("text_dist_"+strDepthLeft+tokenText)] = 1
                
                features[self.featureSet.getId("chain_"+strDepthLeft+chain+"-rev_"+edgeType)] = 1
                self.buildChains(nextToken,sentenceGraph,features,depthLeft-1,chain+"-rev_"+edgeType,edgeSet)

        for edge in outEdges:
            if not edge in visited:
                edgeType = edge[2].get("type")
                features[self.featureSet.getId("dep_"+strDepthLeft+edgeType)] = 1

                nextToken = edge[1]
                for tokenFeature in self.getTokenFeatures(nextToken, sentenceGraph):
                    features[self.featureSet.getId(strDepthLeft + tokenFeature)] = 1
#                for entity in sentenceGraph.tokenIsEntityHead[nextToken]:
#                    if entity.get("isName") == "True":
#                        features[self.featureSet.getId("name_dist_"+strDepthLeft)] = 1
#                        features[self.featureSet.getId("name_dist_"+strDepthLeft+entity.get("type"))] = 1
#                features[self.featureSet.getId("POS_dist_"+strDepthLeft+nextToken.get("POS"))] = 1
#                tokenText = sentenceGraph.getTokenText(nextToken)
#                features[self.featureSet.getId("text_dist_"+strDepthLeft+tokenText)] = 1
                
                features[self.featureSet.getId("chain_"+strDepthLeft+chain+"-frw_"+edgeType)] = 1
                self.buildChains(nextToken,sentenceGraph,features,depthLeft-1,chain+"-frw_"+edgeType,edgeSet)
