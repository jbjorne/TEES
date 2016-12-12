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
        weights = self.model.w_to_normv(token.get("text").lower())
        if weights is not None:
            for i in range(len(weights)):
                self.setFeature("W2V_" + tag + str(i), weights[i])
        else:
            self.setFeature("W2V_" + tag + "None", 1)