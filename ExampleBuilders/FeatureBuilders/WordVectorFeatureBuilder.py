import sys
sys.path.append("..")
from FeatureBuilder import FeatureBuilder
from Utils.Libraries.wvlib_light.lwvlib import WV
import Utils.Settings as Settings
import numpy as np

class WordVectorFeatureBuilder(FeatureBuilder):
    def __init__(self, featureSet, style=None):
        FeatureBuilder.__init__(self, featureSet, style)
        if "wordvector" in style and isinstance(style["wordvector"], basestring):
            wordVectorPath = style["wordvector"]
        else:
            wordVectorPath = Settings.W2VFILE
        print >> sys.stderr, "Loading word vectors from", wordVectorPath
        self.model = WV.load(wordVectorPath, 100000, 10000000) #10000, 500000)
        
    def buildFeatures(self, token, tag=""):
        self.vectorToFeatures(self.model.w_to_normv(token.get("text").lower()), tag)
#         weights = self.model.w_to_normv(token.get("text").lower())
#         if weights is not None:
#             for i in range(len(weights)):
#                 self.setFeature("W2V_" + tag + str(i), weights[i])
#         else:
#             self.setFeature("W2V_" + tag + "None", 1)
    
    def vectorToFeatures(self, vector, tag=""):
        if vector is not None:
            for i in range(len(vector)):
                self.setFeature("W2V_" + tag + str(i), vector[i])
        else:
            self.setFeature("W2V_" + tag + "None", 1)
    
    def buildPathFeatures(self, path):
        if len(path) < 3:
            return
        index = 1
        for token in path[1:-1]:
            self.vectorToFeatures(self.model.w_to_normv(token.get("text").lower()), "path_" + str(index) + "_")
            index += 1
    
    def buildPathPOSFeatures(self, path):
        if len(path) < 3:
            return
        wordByPOS = {}
        for token in path[1:-1]:
            pos = token.get("POS")[0]
            if pos not in wordByPOS:
                wordByPOS[pos] = token.get("text").lower()
        for pos in sorted(wordByPOS.keys()):
            self.vectorToFeatures(self.model.w_to_normv(wordByPOS[pos]), "path" + pos + "_")
            #vector = self.model.w_to_normv(wordByPOS[pos])
            #if vector != None:
            #    vectorToFeatures
    
    def combineTokenVectors(self, tokens, tag):
        vectors = [self.model.w_to_normv(x.get("text").lower()) for x in tokens]
        vectors = [x for x in vectors if x is not None]
        if len(vectors) > 0:
            combined = self.combineVectors(vectors)
            self.vectorToFeatures(combined, tag)
    
    def buildFBAFeatures(self, tokens, t1Index, t2Index):
        if t1Index > t2Index:
            t1Index, t2Index = t2Index, t1Index
        self.combineTokenVectors(tokens[:t1Index], "FB_")
        self.combineTokenVectors(tokens[t1Index+1:t2Index], "B_")
        self.combineTokenVectors(tokens[t1Index+1:], "BA_")
    
    def buildLinearFeatures(self, token, tokens, before=2, after=2, tag=""):
        tokenIndex = tokens.index(token)
        numTokens = len(tokens)
        for i in range(-before, 0) + range(1, 1 + after):
            currentIndex = tokenIndex + i 
            if currentIndex < 0 or currentIndex >= numTokens:
                continue
            self.buildFeatures(tokens[currentIndex], tag + "_lin" + str(i) + "_")   
            
    def combineVectors(self, vectors):
        combined = vectors[0]
        for vector in vectors[1:]:
            combined = np.add(combined, vector)
        return combined / len(vectors)