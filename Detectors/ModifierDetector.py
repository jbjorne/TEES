from SingleStageDetector import SingleStageDetector
from ExampleBuilders.Task3ExampleBuilder import Task3ExampleBuilder
from Classifiers.SVMMultiClassClassifier import SVMMultiClassClassifier
from Evaluators.AveragingMultiClassEvaluator import AveragingMultiClassEvaluator
import Evaluators.BioNLP11GeniaTools

class ModifierDetector(SingleStageDetector):
    def __init__(self):
        SingleStageDetector.__init__(self)
        self.exampleBuilder = Task3ExampleBuilder
        self.classifier = SVMMultiClassClassifier
        self.evaluator = AveragingMultiClassEvaluator
        self.stEvaluator = Evaluators.BioNLP11GeniaTools
        self.tag = "modifier-"