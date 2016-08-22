import sys
sys.path.append("..")
from FeatureBuilder import FeatureBuilder
from Utils.Libraries.wvlib_light.lwvlib import WV
import Utils.Settings as Settings

class WordVectorFeatureBuilder(FeatureBuilder):
    def __init__(self, featureSet, style=None):
        FeatureBuilder.__init__(self, featureSet, style)
        self.model = WV.load(Settings.W2VFILE, 10000, 500000)
        
    def buildFeatures(self, token):
        weights = self.model.w_to_normv(token.get("text").lower())
        #self.setFeature(self.namedEntityCountFeature, 1)