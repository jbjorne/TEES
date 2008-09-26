from FeatureBuilder import FeatureBuilder
import random

class RandomFeatureBuilder(FeatureBuilder):
    def __init__(self, featureSet):
        FeatureBuilder.__init__(self, featureSet)
        self.generator = random.Random(0)
    
    def buildRandomFeatures(self, number, probability):
        for i in range(number):
            if self.generator.random() <= probability:
                self.features[self.featureSet.getId("random"+str(i))] = 1