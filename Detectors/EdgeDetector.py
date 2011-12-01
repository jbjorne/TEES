from SingleStageDetector import SingleStageDetector
from ExampleBuilders.MultiEdgeExampleBuilder import MultiEdgeExampleBuilder
from Classifiers.SVMMultiClassClassifier import SVMMultiClassClassifier
from Evaluators.AveragingMultiClassEvaluator import AveragingMultiClassEvaluator

class EdgeDetector(SingleStageDetector):
    def __init__(self):
        SingleStageDetector.__init__(self)
        self.exampleBuilder = MultiEdgeExampleBuilder
        self.classifier = SVMMultiClassClassifier
        self.evaluator = AveragingMultiClassEvaluator
        self.tag = "edge-"