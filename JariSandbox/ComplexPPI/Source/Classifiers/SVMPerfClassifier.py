import sys,os,copy
sys.path.append("..")
import shutil
import subprocess
import Core.ExampleUtils as Example
import combine
#from Core.Evaluation import Evaluation
from Core.Classifier import Classifier

binDir = "/usr/share/biotext/ComplexPPI/SVMPerf"

defaultOptimizationParameters = {"c":[0.0001,0.001,0.01,0.1,1,10,100]}

class SVMPerfClassifier(Classifier):
    def __init__(self, workDir=None):
        #global tempDir
        
        self._makeTempDir(workDir)
        self.numberOfTrainingExamples = None
    
    def __del__(self):
        self.debugFile.close()
        if self._workDir == None and os.path.exists(self.tempDir):
            print >> sys.stderr, "Removing temporary SVM-perf work directory", self.tempDir
            shutil.rmtree(self.tempDir)
    
    def train(self, examples, parameters=None):
        examples = self.filterTrainingSet(examples)
        parameters = copy.copy(parameters)
        if parameters.has_key("style") and "no_duplicates" in parameters["style"]:
            examples = Example.removeDuplicates(examples)
            del parameters["style"]
        # Convert SVM-light c-values to SVM-perf c-values
        self.numberOfTrainingExamples = len(examples)
        parameters = copy.deepcopy(parameters)
        parameters["c"] = str(float(parameters["c"]) * self.numberOfTrainingExamples / 100.0)
        # Train
        Example.writeExamples(examples, self.tempDir+"/train.dat")
        args = [binDir+"/svm_perf_learn"]
        if parameters != None:
            self.__addParametersToSubprocessCall(args, parameters)
        args += [self.tempDir+"/train.dat", self.tempDir+"/model"]
        subprocess.call(args, stdout = self.debugFile)
        
    def classify(self, examples, parameters=None):
        examples, predictions = self.filterClassificationSet(examples, True)
        Example.writeExamples(examples, self.tempDir+"/test.dat")
        args = [binDir+"/svm_perf_classify"]
        if parameters != None:
            self.__addParametersToSubprocessCall(args, parameters)
        args += [self.tempDir+"/test.dat", self.tempDir+"/model", self.tempDir+"/predictions"]
        subprocess.call(args, stdout = self.debugFile)
        os.remove(self.tempDir+"/model")
        predictionsFile = open(self.tempDir+"/predictions", "rt")
        lines = predictionsFile.readlines()
        predictionsFile.close()
        predictions = []
        for i in range(len(lines)):
            predictions.append( (examples[i],float(lines[i]),"binary") )
        return predictions
    
    def __addParametersToSubprocessCall(self, args, parameters):
        for k,v in parameters.iteritems():
            args.append("-"+k)
            args.append(str(v))