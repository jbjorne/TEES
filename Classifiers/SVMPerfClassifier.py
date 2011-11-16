import sys,os,copy
sys.path.append("..")
import shutil
import subprocess
import Core.ExampleUtils as Example
import combine
#from Core.Evaluation import Evaluation
from Core.Classifier import Classifier
from Classifiers.JoachimsSVMBase import JoachimsSVMBase
import types
import killableprocess

class SVMPerfClassifier(JoachimsSVMBase):
    def __init__(self, workDir=None):
        JoachimsSVMBase.__init__(self, workDir=workDir)
        self.trainBin = "/usr/share/biotext/ComplexPPI/SVMPerf/svm_perf_learn"
        self.classifyBin = "/usr/share/biotext/ComplexPPI/SVMPerf/svm_perf_classify"
        self.type = "binary"
        self.defaultEvaluator = "BinaryEvaluator"
        
        self.numberOfTrainingExamples = None
    
    def train(self, examples, parameters=None):
        if type(examples) == types.StringType:
            trainFilePath = examples
            f = open(trainFilePath,"rt")
            self.numberOfTrainingExamples = len(f.readlines())
            f.close()
        elif type(examples) == types.ListType:
            self.numberOfTrainingExamples = len(examples)
        # Convert SVM-light c-values to SVM-perf c-values
        parameters = copy.deepcopy(parameters)
        parameters["c"] = str(float(parameters["c"]) * self.numberOfTrainingExamples / 100.0)
        # Train
        return JoachimsSVMBase.train(self, examples, parameters)