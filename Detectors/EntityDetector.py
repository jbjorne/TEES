from SingleStageDetector import SingleStageDetector
from ExampleBuilders.EntityExampleBuilder import EntityExampleBuilder
from ExampleWriters.EntityExampleWriter import EntityExampleWriter
from Classifiers.SVMMultiClassClassifier import SVMMultiClassClassifier
from Evaluators.AveragingMultiClassEvaluator import AveragingMultiClassEvaluator

class EntityDetector(SingleStageDetector):
    """
    Detects named entities and triggers.
    """
    def __init__(self):
        SingleStageDetector.__init__(self)
        self.exampleBuilder = EntityExampleBuilder
        self.exampleWriter = EntityExampleWriter()
        self.Classifier = SVMMultiClassClassifier
        self.evaluator = AveragingMultiClassEvaluator
        self.tag = "trigger-"