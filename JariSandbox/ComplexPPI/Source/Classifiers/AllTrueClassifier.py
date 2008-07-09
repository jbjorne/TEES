from Core.Classifier import Classifier

class AllTrueClassifier(Classifier):
    def train(self, examples, parameters=None):        
        pass
    
    def classify(self, examples, parameters=None):
        predictions = []
        for example in examples:
            predictions.append( (example, 1.0) )
        return predictions
