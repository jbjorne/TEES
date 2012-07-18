from SingleStageDetector import SingleStageDetector
from ExampleBuilders.ModifierExampleBuilder import ModifierExampleBuilder
from ExampleWriters.ModifierExampleWriter import ModifierExampleWriter
from Classifiers.SVMMultiClassClassifier import SVMMultiClassClassifier
from Evaluators.AveragingMultiClassEvaluator import AveragingMultiClassEvaluator
import Evaluators.BioNLP11GeniaTools

class ModifierDetector(SingleStageDetector):
    """
    Detects negation and speculation modifiers.
    """
    def __init__(self):
        SingleStageDetector.__init__(self)
        self.exampleBuilder = ModifierExampleBuilder
        self.exampleWriter = ModifierExampleWriter()
        self.Classifier = SVMMultiClassClassifier
        self.evaluator = AveragingMultiClassEvaluator
        self.stEvaluator = Evaluators.BioNLP11GeniaTools
        self.tag = "modifier-"