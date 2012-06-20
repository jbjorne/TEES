from SingleStageDetector import SingleStageDetector
from ExampleBuilders.MultiEdgeExampleBuilder import MultiEdgeExampleBuilder
from ExampleWriters.EdgeExampleWriter import EdgeExampleWriter
from Classifiers.SVMMultiClassClassifier import SVMMultiClassClassifier
from Evaluators.AveragingMultiClassEvaluator import AveragingMultiClassEvaluator

class EdgeDetector(SingleStageDetector):
    def __init__(self):
        SingleStageDetector.__init__(self)
        self.exampleBuilder = MultiEdgeExampleBuilder
        self.exampleWriter = EdgeExampleWriter()
        self.Classifier = SVMMultiClassClassifier
        self.evaluator = AveragingMultiClassEvaluator
        self.tag = "edge-"