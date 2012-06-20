from SingleStageDetector import SingleStageDetector
from ExampleBuilders.GeneralEntityTypeRecognizerGztr import GeneralEntityTypeRecognizerGztr
from ExampleWriters.EntityExampleWriter import EntityExampleWriter
from Classifiers.SVMMultiClassClassifier import SVMMultiClassClassifier
from Evaluators.AveragingMultiClassEvaluator import AveragingMultiClassEvaluator

class TriggerDetector(SingleStageDetector):
    def __init__(self):
        SingleStageDetector.__init__(self)
        self.exampleBuilder = GeneralEntityTypeRecognizerGztr
        self.exampleWriter = EntityExampleWriter()
        self.Classifier = SVMMultiClassClassifier
        self.evaluator = AveragingMultiClassEvaluator
        self.tag = "trigger-"