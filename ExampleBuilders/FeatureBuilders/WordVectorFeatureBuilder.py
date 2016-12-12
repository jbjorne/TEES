import sys
sys.path.append("..")
from FeatureBuilder import FeatureBuilder
from Utils.Libraries.wvlib_light.lwvlib import WV
import Utils.Settings as Settings

class WordVectorFeatureBuilder(FeatureBuilder):
    def __init__(self, featureSet, style=None):
        FeatureBuilder.__init__(self, featureSet, style)
        print >> sys.stderr, "Loading word vectors from", Settings.W2VFILE
        self.model = WV.load(Settings.W2VFILE, 100000, 10000000) #10000, 500000)
        
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