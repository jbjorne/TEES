from Evaluator import Evaluator, EvaluationData
import sys, os, types
import itertools
import subprocess
import tempfile
import shutil
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/..")
import Utils.Settings as Settings
import Utils.ElementTreeUtils as ETUtils
from Detectors.Preprocessor import Preprocessor
from Core.IdSet import IdSet
import Core.ExampleUtils as ExampleUtils
from Evaluators.AveragingMultiClassEvaluator import AveragingMultiClassEvaluator
import json
import math

class ChemProtEvaluator(Evaluator):
    type = "multiclass"
    
    def __init__(self, examples=None, predictions=None, classSet=None):
        if type(classSet) == types.StringType: # class names are in file
            classSet = IdSet(filename=classSet)
        if type(predictions) == types.StringType: # predictions are in file
            predictions = ExampleUtils.loadPredictions(predictions)
        if type(examples) == types.StringType: # examples are in file
            examples = ExampleUtils.readExamples(examples, False)
        
        self.keep = set(["CPR:3", "CPR:4", "CPR:5", "CPR:6", "CPR:9"])

        self.classSet = classSet
        self.results = None
        self.internal = None
        if predictions != None:
            for example in examples:
                if example[3] != None:
                    print >> sys.stderr, "ChemProt Evaluator:"
                    self._calculateExamples(examples, predictions)
                else:
                    print >> sys.stderr, "No example extra info, skipping ChemProt evaluation"
                break
            self.internal = AveragingMultiClassEvaluator(examples, predictions, classSet)
            print >> sys.stderr, "AveragingMultiClassEvaluator:"
            print >> sys.stderr, self.internal.toStringConcise()
    
    def compare(self, evaluation):
        if self.results["F-score"] > evaluation.results["F-score"]:
            return 1
        elif self.results["F-score"] == evaluation.results["F-score"]:
            return 0
        else:
            return -1
    
    def getData(self):
        return self.results["F-score"]
    
    @classmethod
    def evaluate(cls, examples, predictions, classSet=None, outputFile=None, verbose=True):
        """
        Enables using this class without having to manually instantiate it
        """
        evaluator = cls(examples, predictions, classSet)
        if verbose:
            print >> sys.stderr, evaluator.toStringConcise()
        #if outputFile != None:
        #    evaluator.saveCSV(outputFile)
        return evaluator
    
    def _writePredictions(self, examples, predictions, filePath):
        with open(filePath, "wt") as f:
            for example, prediction in itertools.izip(examples, predictions):
                predClassId = prediction[0]
                predClassName = self.classSet.getName(predClassId)
                if predClassName == "neg":
                    continue
                if predClassName not in self.keep:
                    continue
                docId = example[3]["DOID"]
                e1 = example[3]["e1OID"]
                e2 = example[3]["e2OID"]
                f.write("\t".join([docId, predClassName, "Arg1:" + e1, "Arg2:" + e2]) + "\n")
    
    def _prepareEval(self, examples, predictions, tempDir):
        if os.path.exists(tempDir):
            shutil.rmtree(tempDir)
        os.makedirs(tempDir)
        print >> sys.stderr, "Using temporary evaluation directory", tempDir
        predFilePath = os.path.join(tempDir, "predictions.tsv")
        self._writePredictions(examples, predictions, predFilePath)
        return predFilePath
    
    def _calculateExamples(self, examples, predictions):
        tempDir = tempfile.mkdtemp()
        predFilePath = self._prepareEval(examples, predictions, tempDir)
        self.evaluateTSV(predFilePath, tempDir)
        print >> sys.stderr, "Removing temporary evaluation directory", tempDir
        shutil.rmtree(tempDir)
    
    def evaluateTSV(self, predFilePath, tempDir=None):
        removeTempDir = False
        if tempDir == None:
            tempDir = tempfile.mkdtemp()
            removeTempDir = True
        results = self._runEvaluator(predFilePath, "./data/chemprot_development_gold_standard.tsv")
        if math.isnan(results.get("F-score")):
            print >> sys.stderr, "Development set F-score is NaN, attempting evaluation with test set"
            results = self._runEvaluator(predFilePath, "./data/chemprot_test_gold_standard.tsv")
        if removeTempDir:
            print >> sys.stderr, "Removing temporary evaluation directory", tempDir
            shutil.rmtree(tempDir)
        print >> sys.stderr, "ChemProt results:", json.dumps(results)
        self.results = results
        return results
    
    def _runEvaluator(self, predFilePath, goldPath):
        tempDir = tempfile.mkdtemp()
        evaluatorDir = os.path.join(Settings.DATAPATH, "tools", "evaluators", "ChemProtEvaluator")
        removeTemp = False
        if tempDir == None:
            tempDir = tempfile.mkdtemp()
            removeTemp = True
        print >> sys.stderr, "Using temporary evaluation directory", tempDir
        evaluatorTempDir = os.path.join(tempDir, "ChemProtEvaluator")
        shutil.copytree(evaluatorDir, evaluatorTempDir)
        currentDir = os.getcwd()
        os.chdir(evaluatorTempDir)
        command = "java -cp bc6chemprot_eval.jar org.biocreative.tasks.chemprot.main.Main " + os.path.abspath(predFilePath) + " " + goldPath
        print >> sys.stderr, "Running CP17 evaluator: " + command
        p = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        for s in ["".join(x.readlines()).strip() for x in (p.stderr, p.stdout)]:
            if s != "":
                print >> sys.stderr, s
        os.chdir(currentDir)
        results = {}
        with open(os.path.join(evaluatorTempDir, "out", "eval.txt"), "rt") as f:
            for line in f:
                if ":" in line:
                    print >> sys.stderr, line.strip()
                    key, value = [x.strip() for x in line.split(":")]
                    value = float(value) if ("." in value or value == "NaN") else int(value)
                    assert key not in results
                    results[key] = value
        if removeTemp:
            print >> sys.stderr, "Removing temporary evaluation directory", tempDir
            shutil.rmtree(tempDir)
        return results
    
    def toStringConcise(self, indent="", title=None):
        self.internal.toStringConcise(indent, title)
        
    def toDict(self):
        return {x:self.results[x] for x in self.results}

if __name__=="__main__":
    from optparse import OptionParser
    optparser = OptionParser(usage="%prog [options]\nCalculate f-score and other statistics.")
    optparser.add_option("-e", "--examples", default=None, dest="examples", help="", metavar="FILE")
    optparser.add_option("-p", "--predictions", default=None, dest="predictions", help="", metavar="FILE")
    optparser.add_option("-c", "--classSet", default=None, dest="classSet", help="", metavar="FILE")
    optparser.add_option("-d", "--dataSet", default="devel", dest="dataSet", help="", metavar="FILE")
    (options, args) = optparser.parse_args()
    
    assert options.dataSet in ("devel", "test")
    options.dataSet = {"devel":"./data/chemprot_development_gold_standard.tsv", "test":"./data/chemprot_test_gold_standard.tsv"}[options.dataSet]
    
    if options.examples.endswith(".xml") or options.examples.endswith(".xml.gz"):
        preprocessor = Preprocessor(steps="EXPORT_CHEMPROT")
        tempDir = tempfile.mkdtemp()
        tsvPath = os.path.join(tempDir, os.path.basename(options.examples) + ".tsv")
        preprocessor.process(options.examples, tsvPath)
        ChemProtEvaluator().evaluateTSV(tsvPath, options.dataSet)
        shutil.rmtree(tempDir)
    if options.examples.endswith(".tsv"):
        ChemProtEvaluator().evaluateTSV(options.examples, options.dataSet)
    else:
        ev = ChemProtEvaluator(options.examples, options.predictions, options.classSet)
    #print ev.toStringConcise()
