import SingleStageDetector
from ExampleBuilders.GeneralEntityTypeRecognizerGztr import GeneralEntityTypeRecognizerGztr
from Classifiers.SVMMultiClassClassifier import SVMMultiClassClassifier
from Evaluators.AveragingMultiClassEvaluator import AveragingMultiClassEvaluator

class TriggerDetector(SingleStageDetector):
    def __init__(self):
        super(TriggerDetector, self).__init__()
        self.exampleBuilder = GeneralEntityTypeRecognizerGztr
        self.classifier = SVMMultiClassClassifier
        self.evaluator = AveragingMultiClassEvaluator
        self.tag = "trigger_"