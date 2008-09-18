import sys,os
sys.path.append("..")
import shutil
import subprocess
import Core.ExampleUtils as Example
import combine
from Core.Evaluation import Evaluation
from Core.Classifier import Classifier
from Evaluators.MultiClassEvaluator import MultiClassEvaluator

binDir = "/usr/share/biotext/ComplexPPI/SVMMultiClass"

defaultOptimizationParameters = {"c":[0.0001,0.001,0.01,0.1,1,10,100]}

class MajorityClassifier(Classifier):
    def __init__(self, workDir=None):
        self._makeTempDir(workDir)        
    
    def __del__(self):
        self.debugFile.close()
        if self._workDir == None and os.path.exists(self.tempDir):
            print >> sys.stderr, "Removing temporary SVM-multi-class work directory", self.tempDir
            shutil.rmtree(self.tempDir)
    
    def train(self, examples, parameters=None):        
        Example.writeExamples(examples, self.tempDir+"/train.dat")
        classes = {}
        for example in examples:
            if not classes.has_key(example[1]):
               classes[example[1]] = 0
            classes[example[1]] += 1
        for k,v in classes.iteritems:
            
        
    def classify(self, examples, parameters=None):
        Example.writeExamples(examples, self.tempDir+"/test.dat")
        args = [binDir+"/svm_multiclass_classify"]
        if parameters != None:
            self.__addParametersToSubprocessCall(args, parameters)
        args += [self.tempDir+"/test.dat", self.tempDir+"/model", self.tempDir+"/predictions"]
        subprocess.call(args, stdout = self.debugFile)
        
        predictionsFile = open(self.tempDir+"/predictions", "rt")
        lines = predictionsFile.readlines()
        predictionsFile.close()
        predictions = []
        for i in range(len(lines)):
            predictions.append( (examples[i],int(lines[i].split()[0]),"multiclass") )
        return predictions
    
    def __addParametersToSubprocessCall(self, args, parameters):
        for k,v in parameters.iteritems():
            args.append("-"+k)
            args.append(str(v))
