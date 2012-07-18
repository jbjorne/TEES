from SingleStageDetector import SingleStageDetector
from ExampleBuilders.EdgeExampleBuilder import EdgeExampleBuilder
from ExampleWriters.EdgeExampleWriter import EdgeExampleWriter
from Classifiers.SVMMultiClassClassifier import SVMMultiClassClassifier
from Evaluators.AveragingMultiClassEvaluator import AveragingMultiClassEvaluator

class EdgeDetector(SingleStageDetector):
    """
    Detects relations and event arguments.
    """
    def __init__(self):
        SingleStageDetector.__init__(self)
        self.exampleBuilder = EdgeExampleBuilder
        self.exampleWriter = EdgeExampleWriter()
        self.Classifier = SVMMultiClassClassifier
        self.evaluator = AveragingMultiClassEvaluator
        #self.stEvaluator = Evaluators.BioNLP11GeniaTools
        self.tag = "edge-"