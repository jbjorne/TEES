from Detectors.EdgeDetector import EdgeDetector
from Classifiers.AllCorrectClassifier import AllCorrectClassifier
import Utils.Parameters as Parameters

class PairBuilder(EdgeDetector):
    def __init__(self):
        EdgeDetector.__init__(self)
        self.Classifier = AllCorrectClassifier
    
    def train(self, trainData=None, optData=None, model=None, combinedModel=None, exampleStyle=None, 
        classifierParameters=None, parse=None, tokenization=None, task=None, fromStep=None, toStep=None, 
        workDir=None):
        
        exampleStyle = Parameters.cat(exampleStyle, "keep_neg:no_features")
        EdgeDetector.train(self, trainData, optData, model, combinedModel, exampleStyle, classifierParameters, parse, tokenization, fromStep, toStep)
        self.classify(trainData, model, "classification-train/train", goldData=trainData, workDir="classification-train")