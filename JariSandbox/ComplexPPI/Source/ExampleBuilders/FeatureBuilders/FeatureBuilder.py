class FeatureBuilder:
    def __init__(self, featureSet):
        self.featureSet = featureSet
        self.features = None
    
    def setFeatureVector(self, features):
        self.features = features
        
    def normalizeFeatureVector(self):
        # Normalize features
        total = 0.0
        for v in self.features.values(): total += abs(v)
        if total == 0.0: 
            total = 1.0
        for k,v in self.features.iteritems():
            self.features[k] = float(v) / total