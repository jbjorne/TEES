from SingleStageDetector import SingleStageDetector
from ExampleBuilders.GeneralEntityTypeRecognizerGztr import GeneralEntityTypeRecognizerGztr
from Classifiers.SVMMultiClassClassifier import SVMMultiClassClassifier
from Evaluators.AveragingMultiClassEvaluator import AveragingMultiClassEvaluator

class TriggerDetector(SingleStageDetector):
    def __init__(self):
        SingleStageDetector.__init__(self)
        self.exampleBuilder = GeneralEntityTypeRecognizerGztr
        self.Classifier = SVMMultiClassClassifier
        self.evaluator = AveragingMultiClassEvaluator
        self.tag = "trigger-"