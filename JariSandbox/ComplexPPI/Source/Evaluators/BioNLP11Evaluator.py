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

renEvaluatorPath = "/home/jari/data/BioNLP11SharedTask/BioNLP-ST_2011_bacteria_rename_evaluation_sofware/eval_rename.jar"
relEvaluatorPath = ""
coEvaluatorPath = "/home/jari/Downloads/CREvalPackage1.3.zip/CRScorer.jar"

datasets = {}
dataPath = "/home/jari/data/BioNLP11SharedTask/main-tasks/"
datasets["GE"] = [("devel", dataPath+"BioNLP-ST_2011_genia_devel_data_rev1"), 
                  ("train", dataPath+"BioNLP-ST_2011_genia_train_data_rev1")]
datasets["EPI"] = [("devel", dataPath+"BioNLP-ST_2011_Epi_and_PTM_development_data_rev1"), 
                  ("train", dataPath+"BioNLP-ST_2011_Epi_and_PTM_training_data_rev1")]
datasets["ID"] = [("devel", dataPath+"BioNLP-ST_2011_Infectious_Diseases_development_data_rev1"), 
                  ("train", dataPath+"BioNLP-ST_2011_Infectious_Diseases_training_data_rev1")]
datasets["BB"] = [("devel", dataPath+"BioNLP-ST_2011_Bacteria_Biotopes_dev_data_rev1"), 
                  ("train", dataPath+"BioNLP-ST_2011_Bacteria_Biotopes_train_data_rev1")]
datasets["BI"] = [("devel", dataPath+"BioNLP-ST_2011_bacteria_interactions_dev_data_rev1"), 
                  ("train", dataPath+"BioNLP-ST_2011_bacteria_interactions_train_data_rev1")]

evaluatorJars["BB"] = dataPath + "evaluators/BioNLP-ST_2011_Bacteria_Biotopes_evaluation_software/BioNLP-ST_2011_Bacteria_Biotopes_evaluation_software.jar"
evaluatorJars["BI"] = dataPath + "evaluators/BioNLP-ST_2011_bacteria_interactions_evaluation_software/BioNLP-ST_2011_bacteria_interactions_evaluation_software.jar"

def evaluateREN(sourceDir):
    commands = renEvaluatorPath + " " + sourceDir
    p = subprocess.Popen(commands, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stderrLines = p.stderr.readlines()
    for line in stderrLines:
        print >> sys.stderr, line,
    print >> sys.stderr
    stdoutLines = p.stdout.readlines()
    for line in stdoutLines:
        print >> sys.stderr, line,
    print >> sys.stderr

class BioNLP11Evaluator(Evaluator):
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
    
    def evaluateJar(self, task, goldDir, predDir):
        commands = evaluatorJars[task] + " " + goldDir + " " + predDir
        p = subprocess.Popen(commands, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stderrLines = p.stderr.readlines()
        for line in stderrLines:
            print >> sys.stderr, line,
        print >> sys.stderr
        stdoutLines = p.stdout.readlines()
        for line in stdoutLines:
            print >> sys.stderr, line,
        print >> sys.stderr
    
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
    
    def getTaskDir(self, task, dataSet):
        dataDir = os.path.expanduser("~/data/BioNLP11SharedTask")
        subTask = None
        if "." in task:
            task, subTask = task.split(".")
        if task == "GE":
            return dataDir
