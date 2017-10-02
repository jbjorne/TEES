from Evaluator import Evaluator, EvaluationData
import sys, os, types
import itertools
import subprocess
import tempfile
import shutil
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/..")
import Utils.Settings as Settings
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/..")
from Core.IdSet import IdSet
import Core.ExampleUtils as ExampleUtils

class ChemProtEvaluator(Evaluator):
    def __init__(self, examples, predictions=None, classSet=None):
        if type(classSet) == types.StringType: # class names are in file
            classSet = IdSet(filename=classSet)
        if type(predictions) == types.StringType: # predictions are in file
            predictions = ExampleUtils.loadPredictions(predictions)
        if type(examples) == types.StringType: # examples are in file
            examples = ExampleUtils.readExamples(examples, False)

        self.classSet = classSet
        
        if predictions != None:
            self._calculate(examples, predictions)
    
    @classmethod
    def evaluate(cls, examples, predictions, classSet=None, outputFile=None, verbose=True):
        """
        Enables using this class without having to manually instantiate it
        """
        evaluator = cls(examples, predictions, classSet)
        if verbose:
            print >> sys.stderr, evaluator.toStringConcise()
        if outputFile != None:
            evaluator.saveCSV(outputFile)
        return evaluator
    
    def _writePredictions(self, examples, predictions, filePath):
        with open(filePath, "wt") as f:
            for example, prediction in itertools.izip(examples, predictions):
                predClassId = prediction[0]
                predClassName = self.classSet.getName(predClassId)
                if predClassName == "neg":
                    continue
                docId = example[3]["DOID"]
                e1 = example[3]["e1OID"]
                e2 = example[3]["e2OID"]
                f.write("\t".join([docId, predClassName, "Arg1:" + e1, "Arg2:" + e2]) + "\n")
    
    def _calculate(self, examples, predictions):
        tempDir = tempfile.mkdtemp()
        print >> sys.stderr, "Using temporary evaluation directory", tempDir
        predFilePath = os.path.join(tempDir, "predictions.tsv")
        self._writePredictions(examples, predictions, predFilePath)
        evaluatorDir = os.path.join(Settings.DATAPATH, "tools", "evaluators", "ChemProtEvaluator")
        evaluatorTempDir = os.path.join(tempDir, "ChemProtEvaluator")
        shutil.copytree(evaluatorDir, evaluatorTempDir)
        currentDir = os.getcwd()
        os.chdir(evaluatorTempDir)
        command = "java -cp bc6chemprot_eval.jar org.biocreative.tasks.chemprot.main.Main " + os.path.abspath(predFilePath) + " ./data/chemprot_development_gold_standard.tsv"
        print >> sys.stderr, "Running CP17 evaluator: " + command
        p = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        for s in ["".join(x.readlines()).strip() for x in (p.stderr, p.stdout)]:
            if s != "":
                print >> sys.stderr, s
        results = {}
        with open(os.path.join(evaluatorTempDir, "out", "eval.txt"), "rt") as f:
            for line in f:
                if ":" in line:
                    print >> sys.stderr, line.strip()
                    key, value = [x.strip() for x in line.split(":")]
                    value = float(value) if "." in value else int(value)
                    assert key not in results
                    results[key] = value
        os.chdir(currentDir)
        self.results = results
        #shutil.rmtree(tempDir)

if __name__=="__main__":
    from optparse import OptionParser
    optparser = OptionParser(usage="%prog [options]\nCalculate f-score and other statistics.")
    optparser.add_option("-e", "--examples", default=None, dest="examples", help="", metavar="FILE")
    optparser.add_option("-p", "--predictions", default=None, dest="predictions", help="", metavar="FILE")
    optparser.add_option("-c", "--classSet", default=None, dest="classSet", help="", metavar="FILE")
    (options, args) = optparser.parse_args()
    
    ev = ChemProtEvaluator(options.examples, options.predictions, options.classSet)
    #print ev.toStringConcise()