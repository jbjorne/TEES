"""
Base class for classifiers
"""

class Classifier:
    def train(self, examples, outDir, parameters, classifyExamples=None):        
        pass
    
    def classify(self, examples, output, model=None):
        raise NotImplementedError
    
    def optimize(self, examples, outDir, parameters, classifyExamples, classIds, step="BOTH", evaluator=None, determineThreshold=False, timeout=None, downloadAllModels=False):
        pass