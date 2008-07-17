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

class SVMMultiClassClassifier(Classifier):
    def __init__(self, workDir=None):
        #global tempDir
        
        self._makeTempDir(workDir)        
    
    def __del__(self):
        self.debugFile.close()
        if self._workDir == None and os.path.exists(self.tempDir):
            print >> sys.stderr, "Removing temporary SVM-multi-class work directory", self.tempDir
            shutil.rmtree(self.tempDir)
    
    def train(self, examples, parameters=None):        
        Example.writeExamples(examples, self.tempDir+"/train.dat")
        args = [binDir+"/svm_multiclass_learn"]
        if parameters != None:
            self.__addParametersToSubprocessCall(args, parameters)
        args += [self.tempDir+"/train.dat", self.tempDir+"/model"]
        subprocess.call(args, stdout = self.debugFile)
        
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
    
#    def optimize(self, trainExamples, classifyExamples, parameters=defaultOptimizationParameters, evaluationClass=Evaluation, evaluationArgs=None):
#        return Classifier.optimize(self, trainExamples, classifyExamples, parameters, MultiClassEvaluator, None)

