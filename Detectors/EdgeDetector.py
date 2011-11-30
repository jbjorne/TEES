import SingleStageDetector
from ExampleBuilders.MultiEdgeExampleBuilder import MultiEdgeExampleBuilder
from Classifiers.SVMMultiClassClassifier import SVMMultiClassClassifier
from Evaluators.AveragingMultiClassEvaluator import AveragingMultiClassEvaluator

class EdgeDetector(SingleStageDetector):
    def __init__(self):
        super(EdgeDetector, self).__init__()
        self.exampleBuilder = MultiEdgeExampleBuilder
        self.classifier = SVMMultiClassClassifier
        self.evaluator = AveragingMultiClassEvaluator
        self.tag = "edge_"