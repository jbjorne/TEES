class FeatureBuilder:
    def __init__(self, featureSet):
        self.featureSet = featureSet
        self.features = None
        self.entity1 = None
        self.entity2 = None
    
    def setFeatureVector(self, features, entity1=None, entity2=None):
        self.features = features
        self.entity1 = entity1
        self.entity2 = entity2
        
    def normalizeFeatureVector(self):
        # Normalize features
        total = 0.0
        for v in self.features.values(): total += abs(v)
        if total == 0.0: 
            total = 1.0
        for k,v in self.features.iteritems():
            self.features[k] = float(v) / total