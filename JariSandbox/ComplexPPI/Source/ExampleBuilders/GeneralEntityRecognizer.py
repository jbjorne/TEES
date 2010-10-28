import sys
sys.path.append("..")
from Core.ExampleBuilder import ExampleBuilder
import Stemming.PorterStemmer as PorterStemmer
from FeatureBuilders.EdgeFeatureBuilder import EdgeFeatureBuilder
from FeatureBuilders.TokenFeatureBuilder import TokenFeatureBuilder

def loadRelexInteractionWords(filename):
    print >> sys.stderr, "Loading interaction words from", filename
    allWords = []
    wordDict = {}
    f = open(filename)
    for line in f:
        line = line.strip()
        stem, words = line.split(":")
        words = words.split("|")
        for word in words:
            wordDict[word] = stem
        allWords.extend(words)
    f.close()
    return allWords, wordDict

intWords, wordDict = loadRelexInteractionWords("/home/jari/cvs_checkout/JariSandbox/PPIDependencies/Data/InteractionWordsRelexBioInfer.riw")

class GeneralEntityRecognizer(ExampleBuilder):
    
    def __init__(self):
        ExampleBuilder.__init__(self)
        self.edgeFeatureBuilder = EdgeFeatureBuilder(self.featureSet)
        self.entityFeatureBuilder = TokenFeatureBuilder(self.featureSet)
        
    def buildExamples(self, sentenceGraph, exampleIndex = 0):
        examples = []
        #exampleIndex = 0
        
        namedEntityCount = 0
        for i in range(len(sentenceGraph.tokens)):
            token = sentenceGraph.tokens[i]
            if sentenceGraph.tokenIsName[token]:
                namedEntityCount += 1
        for i in range(len(sentenceGraph.tokens)):
            token = sentenceGraph.tokens[i]
            # Recognize only non-named entities (i.e. interaction words)
            if sentenceGraph.tokenIsName[token]:
                continue
            
            if sentenceGraph.tokenIsEntityHead[token] != None:
            # CLASS
                category = 1
            else:
                category = -1
            
            # FEATURES
            features = {}
            # Main features
            textUpper = token.get("text")
            text = textUpper.lower()
            features[self.featureSet.getId("txt_"+text)] = 1
            features[self.featureSet.getId("POS_"+token.get("POS"))] = 1
            stem = PorterStemmer.stem(text)
            features[self.featureSet.getId("stem_"+stem)] = 1
            features[self.featureSet.getId("nonstem_"+text[len(stem):])] = 1
            # Dictionary features
            if text in intWords:
                features[self.featureSet.getId("dict")] = 1
                features[self.featureSet.getId("dict_def_"+wordDict[text])]=1
            # Named entity count
            features[self.featureSet.getId("neCount")] = namedEntityCount
            # Linear order features
            self.entityFeatureBuilder.setFeatureVector(features)
            self.entityFeatureBuilder.buildLinearOrderFeatures(i, sentenceGraph, 3, 3 )
            # Content
            self.entityFeatureBuilder.buildContentFeatures(i, textUpper, duplets=True, triplets=True)
            self.entityFeatureBuilder.setFeatureVector(None)
            # Attached edges
            self.edgeFeatureBuilder.setFeatureVector(features)
            t1InEdges = sentenceGraph.dependencyGraph.in_edges(token)
            for edge in t1InEdges:
                self.edgeFeatureBuilder.buildEdgeFeatures(edge, sentenceGraph, "in_", text=True, POS=True, annType=False, maskNames=True)
#                l2Edges = sentenceGraph.dependencyGraph.in_edges(edge[0])
#                for e2 in l2Edges:
#                    self.featureBuilder.buildEdgeFeatures(edge, sentenceGraph, "in2_", text=True, POS=True, annType=False, maskNames=True)
#                l2Edges = sentenceGraph.dependencyGraph.out_edges(edge[0])
#                for e2 in l2Edges:
#                    self.featureBuilder.buildEdgeFeatures(edge, sentenceGraph, "in2_", text=True, POS=True, annType=False, maskNames=True)
                #self.featureBuilder.buildAttachedEdgeFeatures(edge, sentenceGraph, "in_att_", text=True, POS=True, annType=False, maskNames=True)       
                #self.featureBuilder.buildLinearOrderFeatures(edge)
            t1OutEdges = sentenceGraph.dependencyGraph.out_edges(token)
            for edge in t1OutEdges:
                self.edgeFeatureBuilder.buildEdgeFeatures(edge, sentenceGraph, "out_", text=True, POS=True, annType=False, maskNames=True)
#                l2Edges = sentenceGraph.dependencyGraph.in_edges(edge[1])
#                for e2 in l2Edges:
#                    self.featureBuilder.buildEdgeFeatures(edge, sentenceGraph, "out2_", text=True, POS=True, annType=False, maskNames=True)
#                l2Edges = sentenceGraph.dependencyGraph.out_edges(edge[1])
#                for e2 in l2Edges:
#                    self.featureBuilder.buildEdgeFeatures(edge, sentenceGraph, "out2_", text=True, POS=True, annType=False, maskNames=True)
                #self.featureBuilder.buildAttachedEdgeFeatures(edge, sentenceGraph, "out_att_", text=True, POS=True, annType=False, maskNames=True)       
                #self.featureBuilder.buildLinearOrderFeatures(edge)
            self.edgeFeatureBuilder.setFeatureVector(None)
             
            extra = {"xtype":"token","t":token}
            examples.append( (sentenceGraph.getSentenceId()+".x"+str(exampleIndex),category,features,extra) )
            exampleIndex += 1
        return examples