import sys,os
sys.path.append("..")
import shutil
import subprocess
import Core.ExampleUtils as Example
import combine
from Core.Evaluation import Evaluation
from Core.Classifier import Classifier
import Core.Split as Split
from Evaluators.MultiClassEvaluator import MultiClassEvaluator

binDir = "/usr/share/biotext/ComplexPPI/SVMMultiClass"

defaultOptimizationParameters = {"c":[0.0001,0.001,0.01,0.1,1,10,100]}

class SVMMultiClassClassifier(Classifier):
    def __init__(self, workDir=None, negRatio=None):
        #global tempDir
        self.negRatio = None
        self._makeTempDir(workDir)        
    
    def __del__(self):
        self.debugFile.close()
        if self._workDir == None and os.path.exists(self.tempDir):
            print >> sys.stderr, "Removing temporary SVM-multi-class work directory", self.tempDir
            shutil.rmtree(self.tempDir)
    
    def train(self, examples, parameters=None):
        examples = self.filterTrainingSet(examples)
        if self.negRatio != None:
            examples = self.downSampleNegatives(examples, self.negRatio)
        Example.writeExamples(examples, self.tempDir+"/train.dat")
        args = [binDir+"/svm_multiclass_learn"]
        if parameters != None:
            self.__addParametersToSubprocessCall(args, parameters)
        args += [self.tempDir+"/train.dat", self.tempDir+"/model"]
        subprocess.call(args, stdout = self.debugFile)
        
    def classify(self, examples, parameters=None):
        examples, predictions = self.filterClassificationSet(examples, False)
        Example.writeExamples(examples, self.tempDir+"/test.dat")
        args = [binDir+"/svm_multiclass_classify"]
        if parameters != None:
            self.__addParametersToSubprocessCall(args, parameters)
        args += [self.tempDir+"/test.dat", self.tempDir+"/model", self.tempDir+"/predictions"]
        subprocess.call(args, stdout = self.debugFile)
        os.remove(self.tempDir+"/model")
        predictionsFile = open(self.tempDir+"/predictions", "rt")
        lines = predictionsFile.readlines()
        predictionsFile.close()
        #predictions = []
        for i in range(len(lines)):
            predictions.append( (examples[i],int(lines[i].split()[0]),"multiclass") )
        return predictions
    
    def __addParametersToSubprocessCall(self, args, parameters):
        for k,v in parameters.iteritems():
            args.append("-"+k)
            args.append(str(v))

    def downSampleNegatives(self, examples, ratio):
        positives = []
        negatives = []
        for example in examples:
            if example[1] == 1:
                negatives.append(example)
            else:
                positives.append(example)
        
        targetNumNegatives = ratio * len(positives)
        if targetNumNegatives > len(negatives):
            targetNumNegatives = len(negatives)
        sample = Split.getSample(len(negatives), targetNumNegatives / float(len(negatives)) )
        examples = positives
        for i in range(len(sample)):
            if sample[i] == 0:
                examples.append(negatives[i])
        return examples

    
#    def optimize(self, trainExamples, classifyExamples, parameters=defaultOptimizationParameters, evaluationClass=Evaluation, evaluationArgs=None):
#        return Classifier.optimize(self, trainExamples, classifyExamples, parameters, MultiClassEvaluator, None)

