"""
For BioNLP'09 Shared Task format data (.a2)
"""
from Evaluator import Evaluator
from Evaluator import EvaluationData
from AveragingMultiClassEvaluator import AveragingMultiClassEvaluator
import sys, os, types
thisPath = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(thisPath,".."))
from Core.IdSet import IdSet
import Core.ExampleUtils as ExampleUtils
import Core.SentenceGraph
from ExampleWriters.BioTextExampleWriter import BioTextExampleWriter
import BioNLP11GeniaTools
import InteractionXML as ix

import STFormat.ConvertXML

class BXEvaluator(Evaluator):
    type = "multiclass"
    
    def __init__(self, examples, predictions=None, classSet=None):
        if type(classSet) == types.StringType: # class names are in file
            classSet = IdSet(filename=classSet)
        if type(predictions) == types.StringType: # predictions are in file
            predictions = ExampleUtils.loadPredictions(predictions)
        if type(examples) == types.StringType: # examples are in file
            examples = ExampleUtils.readExamples(examples, False)
        
        corpusElements = Core.SentenceGraph.loadCorpus(BXEvaluator.corpusFilename, BXEvaluator.parse, BXEvaluator.tokenization)
        # Build interaction xml
        xml = BioTextExampleWriter.write(examples, predictions, corpusElements, None, BXEvaluator.ids+".class_names", BXEvaluator.parse, BXEvaluator.tokenization)
        xml = ix.splitMergedElements(xml, None)
        xml = ix.recalculateIds(xml, None, True)
        #xml = ExampleUtils.writeToInteractionXML(examples, predictions, SharedTaskEvaluator.corpusElements, None, "genia-direct-event-ids.class_names", SharedTaskEvaluator.parse, SharedTaskEvaluator.tokenization)
        # Convert to GENIA format
        STFormat.ConvertXML.toSTFormat(xml, BXEvaluator.geniaDir, outputTag="a2")
        #gifxmlToGenia(xml, BXEvaluator.geniaDir, task=SharedTaskEvaluator.task, verbose=False)
        # Use GENIA evaluation tool
        self.results = BioNLP11GeniaTools.evaluateBX(BXEvaluator.geniaDir, corpusName=BXEvaluator.corpusTag)
        corpusElements = None
        
    @classmethod
    def evaluate(cls, examples, predictions, classSet=None, outputFile=None):
        """
        Enables using this class without having to manually instantiate it
        """
        # First make an example level evaluation
        AveragingMultiClassEvaluator.evaluate(examples, predictions, classSet=classSet, outputFile=None)
        
        # Then use the Shared Task evaluation system
        evaluator = cls(examples, predictions, classSet)
        #print >> sys.stderr, evaluator.toStringConcise()
        #if outputFile != None:
        #    evaluator.saveCSV(outputFile)
        return evaluator

    def compare(self, evaluation):
        #print "Self", self.results
        #print "Evaluation", evaluation.results
        if self.results["fscore"] > evaluation.results["fscore"]:
            return 1
        elif self.results["fscore"] == evaluation.results["fscore"]:
            return 0
        else:
            return -1
    
    @classmethod
    def setOptions(cls, geniaDir, corpusTag, corpus, parse=None, tokenization=None, ids=None):
        """
        Set the options required for converting examples into interaction XML.
        Currently, this can't be done through a method parameter due to the
        way OptimizeParameters uses Evaluators.
        
        geniaDir - working directory that will be filled with genia files
        task - 1 or 2
        corpus - filename of CorpusElements-object, must be the source of the examples
        parse - required if corpus == filename
        tokenization - required if corpus == filename
        """
        BXEvaluator.geniaDir = geniaDir
        BXEvaluator.corpusTag = corpusTag
        BXEvaluator.parse = parse
        BXEvaluator.ids = ids
        BXEvaluator.tokenization = tokenization
        BXEvaluator.corpusFilename = corpus
#        if type(corpus) == types.StringType or isinstance(corpus,ET.ElementTree): # corpus is in file
#            import Core.SentenceGraph
#            SharedTaskEvaluator.corpusElements = Core.SentenceGraph.loadCorpus(corpus, parse, tokenization)
#        else:
#            SharedTaskEvaluator.corpusElements = corpus
