from SingleStageDetector import SingleStageDetector
from ExampleBuilders.UnmergingExampleBuilder import UnmergingExampleBuilder
from ExampleWriters.UnmergingExampleWriter import UnmergingExampleWriter
from Classifiers.SVMMultiClassClassifier import SVMMultiClassClassifier
from Evaluators.AveragingMultiClassEvaluator import AveragingMultiClassEvaluator

class UnmergingDetector(SingleStageDetector):
    """
    Makes valid argument combinations for BioNLP type events.
    """
    def __init__(self):
        SingleStageDetector.__init__(self)
        self.exampleBuilder = UnmergingExampleBuilder
        self.exampleWriter = UnmergingExampleWriter()
        self.Classifier = SVMMultiClassClassifier
        self.evaluator = AveragingMultiClassEvaluator
        self.tag = "unmerging-"