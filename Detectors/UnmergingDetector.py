from SingleStageDetector import SingleStageDetector
from ExampleBuilders.UnmergingExampleBuilder import UnmergingExampleBuilder
from ExampleWriters.UnmergingExampleWriter import UnmergingExampleWriter
from Classifiers.SVMMultiClassClassifier import SVMMultiClassClassifier
from Evaluators.AveragingMultiClassEvaluator import AveragingMultiClassEvaluator
import itertools, sys, os

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
    
    def buildExamples(self, model, datas, outputs, golds=[], exampleStyle=None, saveIdsToModel=False, parse=None):
        if exampleStyle == None:
            exampleStyle = model.getStr(self.tag+"example-style")
        if parse == None:
            parse = self.getStr(self.tag+"parse", model)
        self.structureAnalyzer.load(model)
        self.exampleBuilder.structureAnalyzer = self.structureAnalyzer
        for data, output, gold in itertools.izip_longest(datas, outputs, golds, fillvalue=[]):
            print >> sys.stderr, "Example generation for", output
            if not isinstance(data, (list, tuple)): data = [data]
            if not isinstance(gold, (list, tuple)): gold = [gold]
            append = False
            for dataSet, goldSet in itertools.izip_longest(data, gold, fillvalue=None):
                if goldSet == None:
                    goldSet = dataSet
                if dataSet != None:
                    self.exampleBuilder.run(dataSet, output, parse, None, exampleStyle, model.get(self.tag+"ids.classes", 
                        True), model.get(self.tag+"ids.features", True), goldSet, append, saveIdsToModel,
                        structureAnalyzer=self.structureAnalyzer)
                append = True
        if saveIdsToModel:
            model.save()