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

RELEASE = True
#IF LOCAL
RELEASE = False
#ENDIF
if RELEASE:
    sys.path.append(os.path.abspath(os.path.join(thisPath, "../SharedTask/formatConversion")))
    from gifxmlToGenia import gifxmlToGenia
    sys.path.append(os.path.abspath(os.path.join(thisPath, "../SharedTask")))
#IF LOCAL
else:
    sys.path.append(os.path.abspath(os.path.join(thisPath, "../../../../GeniaChallenge/formatConversion")))
    from gifxmlToGenia import gifxmlToGenia
    sys.path.append(os.path.abspath(os.path.join(thisPath, "../../../../GeniaChallenge")))
#ENDIF
import evaluation.EvaluateSharedTask
evaluateSharedTask = evaluation.EvaluateSharedTask.evaluate

class SharedTaskEvaluator(Evaluator):
    type = "multiclass"
    
    def __init__(self, examples, predictions=None, classSet=None):
        if type(classSet) == types.StringType: # class names are in file
            classSet = IdSet(filename=classSet)
        if type(predictions) == types.StringType: # predictions are in file
            predictions = ExampleUtils.loadPredictions(predictions)
        if type(examples) == types.StringType: # examples are in file
            examples = ExampleUtils.readExamples(examples, False)
        
        SharedTaskEvaluator.corpusElements = Core.SentenceGraph.loadCorpus(SharedTaskEvaluator.corpusFilename, SharedTaskEvaluator.parse, SharedTaskEvaluator.tokenization)
        # Build interaction xml
        xml = BioTextExampleWriter.write(examples, predictions, SharedTaskEvaluator.corpusElements, None, SharedTaskEvaluator.ids+".class_names", SharedTaskEvaluator.parse, SharedTaskEvaluator.tokenization)
        #xml = ExampleUtils.writeToInteractionXML(examples, predictions, SharedTaskEvaluator.corpusElements, None, "genia-direct-event-ids.class_names", SharedTaskEvaluator.parse, SharedTaskEvaluator.tokenization)
        # Convert to GENIA format
        gifxmlToGenia(xml, SharedTaskEvaluator.geniaDir, task=SharedTaskEvaluator.task, verbose=False)
        # Use GENIA evaluation tool
        self.results = evaluateSharedTask(SharedTaskEvaluator.geniaDir, task=SharedTaskEvaluator.task, evaluations=["approximate"], verbose=False)
    
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
        if self.results["approximate"]["ALL-TOTAL"]["fscore"] > evaluation.results["approximate"]["ALL-TOTAL"]["fscore"]:
            return 1
        elif self.results["approximate"]["ALL-TOTAL"]["fscore"] == evaluation.results["approximate"]["ALL-TOTAL"]["fscore"]:
            return 0
        else:
            return -1
    
    @classmethod
    def setOptions(cls, geniaDir, task, corpus, parse=None, tokenization=None, ids=None):
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
        SharedTaskEvaluator.geniaDir = geniaDir
        SharedTaskEvaluator.task = task
        SharedTaskEvaluator.parse = parse
        SharedTaskEvaluator.ids = ids
        SharedTaskEvaluator.tokenization = tokenization
        SharedTaskEvaluator.corpusFilename = corpus
        if type(corpus) == types.StringType or isinstance(corpus,ET.ElementTree): # corpus is in file
            import Core.SentenceGraph
            SharedTaskEvaluator.corpusElements = Core.SentenceGraph.loadCorpus(corpus, parse, tokenization)
        else:
            SharedTaskEvaluator.corpusElements = corpus
